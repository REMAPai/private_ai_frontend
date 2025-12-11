import json
import logging
from typing import Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session
from starlette.responses import Response

from open_webui.internal.db import SessionLocal
from open_webui.models.users import User  # Import User model so SQLAlchemy can resolve foreign keys
from token_gateway.config import Settings, get_settings
from token_gateway.llm_providers import get_provider
from token_gateway.utils import (
    SimpleRateLimiter,
    enforce_quota,
    estimate_tokens_from_prompt,
    get_user_from_headers,
    record_usage,
    resolve_limits,
)

logger = logging.getLogger(__name__)

router = APIRouter()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def require_gateway_key(request: Request, settings: Settings = Depends(get_settings)):
    configured_key = settings.gateway_api_key
    if not configured_key:
        return

    header = request.headers.get("Authorization", "")
    provided = None
    if header.lower().startswith("bearer "):
        provided = header.split(" ", 1)[1].strip()
    provided = provided or request.headers.get("x-api-key")

    if provided != configured_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing gateway API key",
        )


def get_provider_name(request: Request, settings: Settings) -> str:
    return request.headers.get("X-LLM-Provider", settings.default_provider)


def _provider_configs(settings: Settings) -> Dict[str, any]:
    return {
        "openai": settings.openai,
        "anthropic": settings.anthropic,
        "gemini": settings.gemini,
    }


async def _forward_request(
    path: str,
    request: Request,
    db: Session,
    settings: Settings,
) -> Response:
    provider_name = get_provider_name(request, settings)
    provider = get_provider(_provider_configs(settings), provider_name)

    raw_payload: Optional[dict] = None
    if request.method in ("POST", "PUT", "PATCH"):
        raw_payload = await request.json()

    user_id = get_user_from_headers(request.headers)
    rate_limiter: SimpleRateLimiter = request.app.state.rate_limiter

    try:
        allowed, usage_row, _, _ = resolve_limits(db, user_id, settings)
    except Exception as e:
        logger.exception(f"Error resolving limits for user {user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error: {str(e)}",
        )

    ok, retry_after = await rate_limiter.check(user_id)
    if not ok:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many requests",
            headers={"Retry-After": f"{int(retry_after)}"},
        )

    estimated_tokens = estimate_tokens_from_prompt(raw_payload or {})
    try:
        enforce_quota(db, user_id, estimated_tokens, settings)
    except HTTPException as exc:
        exc.headers = exc.headers or {}
        exc.headers["X-Tokens-Allowed"] = str(allowed)
        exc.headers["X-Tokens-Used"] = str(usage_row.used_tokens)
        raise

    # Forward the request
    query_params = dict(request.query_params)
    response = await provider.forward(
        path,
        raw_payload,
        dict(request.headers),
        method=request.method,
        params=query_params,
    )

    # Update usage; for streaming responses we fall back to the estimate
    tokens_used = estimated_tokens
    if not hasattr(response, "body_iterator") and response.media_type and "json" in response.media_type.lower():
        try:
            body = response.body
            parsed = json.loads(body)
            usage = parsed.get("usage") if isinstance(parsed, dict) else None
            if usage:
                tokens_used = (
                    usage.get("total_tokens")
                    or usage.get("token_count")
                    or tokens_used
                )
        except Exception as e:
            logger.debug(f"Unable to parse usage from response: {e}")

    record_usage(db, usage_row, tokens_used)
    return response


@router.get("/health")
async def health():
    return {"status": "ok"}


@router.get("/models", dependencies=[Depends(require_gateway_key)])
async def list_models_short(
    request: Request,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    """Compatibility endpoint: /models -> /v1/models"""
    try:
        return await _forward_request("/v1/models", request, db, settings)
    except Exception as e:
        logger.exception(f"Error in list_models_short: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}",
        )


@router.get("/v1/models", dependencies=[Depends(require_gateway_key)])
async def list_models(
    request: Request,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    try:
        return await _forward_request("/v1/models", request, db, settings)
    except Exception as e:
        logger.exception(f"Error in list_models: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}",
        )


@router.post(
    "/v1/chat/completions",
    dependencies=[Depends(require_gateway_key)],
)
async def chat_completions(
    request: Request,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    return await _forward_request("/v1/chat/completions", request, db, settings)


@router.post(
    "/v1/embeddings",
    dependencies=[Depends(require_gateway_key)],
)
async def embeddings(
    request: Request,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    return await _forward_request("/v1/embeddings", request, db, settings)


@router.post(
    "/v1/images/generations",
    dependencies=[Depends(require_gateway_key)],
)
async def image_generations(
    request: Request,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    return await _forward_request("/v1/images/generations", request, db, settings)


