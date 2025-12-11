import logging
from typing import Any, Dict, Optional

import httpx
from fastapi import HTTPException, status
from starlette.responses import StreamingResponse, Response
from starlette.background import BackgroundTask

from token_gateway.config import ProviderConfig

logger = logging.getLogger(__name__)


def _filtered_headers(headers: httpx.Headers) -> Dict[str, str]:
    # Remove hop-by-hop headers that FastAPI should not forward
    hop_by_hop = {
        "connection",
        "keep-alive",
        "proxy-authenticate",
        "proxy-authorization",
        "te",
        "trailers",
        "transfer-encoding",
        "upgrade",
    }
    return {k: v for k, v in headers.items() if k.lower() not in hop_by_hop}


class OpenAICompatibleProvider:
    def __init__(self, config: ProviderConfig):
        self.config = config

    async def forward(
        self,
        path: str,
        payload: Optional[Dict[str, Any]],
        headers: Dict[str, str],
        method: str = "POST",
        params: Optional[Dict[str, Any]] = None,
    ) -> Response:
        # Filter out headers that shouldn't be forwarded to the provider
        # Remove Authorization, Host, Content-Length, and other gateway-specific headers
        # Content-Length is removed because we're reconstructing the body and httpx will calculate it
        filtered_headers = {
            k: v for k, v in headers.items()
            if k.lower() not in ("authorization", "host", "content-length", "x-forwarded-for", "x-forwarded-proto", "x-forwarded-host")
        }
        
        # Ensure we have a provider API key
        if not self.config.api_key or not self.config.api_key.strip():
            logger.error(f"Provider {self.config.name} API key is not configured")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Provider {self.config.name} API key is not configured",
            )
        
        request_headers = {
            **filtered_headers,
            "Authorization": f"Bearer {self.config.api_key.strip()}",
        }

        # Strip /v1 from path if base_url already ends with /v1
        clean_path = path.lstrip('/')
        if self.config.base_url.rstrip('/').endswith('/v1') and clean_path.startswith('v1/'):
            clean_path = clean_path[3:]  # Remove 'v1/' prefix
        
        url = f"{self.config.base_url.rstrip('/')}/{clean_path}"
        
        logger.info(f"Forwarding {method} request to {url} for provider {self.config.name}")
        logger.debug(f"Request headers (excluding Authorization): {[k for k in request_headers.keys() if k.lower() != 'authorization']}")
        
        # Create client without context manager for streaming responses
        client = httpx.AsyncClient(timeout=httpx.Timeout(60.0, connect=10.0), follow_redirects=True)
        
        try:
            # Make the request with streaming enabled
            request = client.build_request(
                method,
                url,
                json=payload if method.upper() != "GET" else None,
                params=params,
                headers=request_headers,
            )
            
            # Send request and get response
            resp = await client.send(request, stream=True)
            content_type = resp.headers.get("content-type", "")
            
            if "text/event-stream" in content_type:
                # For streaming responses, create iterator that reads from response
                # Close client and response after streaming completes
                async def iterator():
                    try:
                        async for chunk in resp.aiter_bytes():
                            yield chunk
                    except Exception as e:
                        logger.error(f"Error streaming response: {e}")
                        raise
                    finally:
                        # Clean up: close response and client
                        try:
                            await resp.aclose()
                        except Exception:
                            pass
                        try:
                            await client.aclose()
                        except Exception:
                            pass
                
                # Background task to ensure cleanup
                async def cleanup():
                    try:
                        await resp.aclose()
                    except Exception:
                        pass
                    try:
                        await client.aclose()
                    except Exception:
                        pass
                
                return StreamingResponse(
                    iterator(),
                    status_code=resp.status_code,
                    headers=_filtered_headers(resp.headers),
                    media_type="text/event-stream",
                    background=BackgroundTask(cleanup),
                )

            # For non-streaming responses, read the body and close everything
            try:
                body = await resp.aread()
                
                # Log error responses for debugging
                if resp.status_code >= 400:
                    try:
                        error_body = body.decode('utf-8') if body else ""
                        logger.error(f"Provider {self.config.name} returned {resp.status_code}: {error_body[:500]}")
                    except Exception:
                        logger.error(f"Provider {self.config.name} returned {resp.status_code} (unable to decode response body)")
                
                return Response(
                    content=body,
                    status_code=resp.status_code,
                    headers=_filtered_headers(resp.headers),
                    media_type=content_type or None,
                )
            finally:
                await resp.aclose()
                await client.aclose()
                
        except Exception as e:
            # Ensure cleanup on error
            try:
                await client.aclose()
            except Exception:
                pass
            raise


def get_provider(configs: Dict[str, ProviderConfig], provider_name: str) -> OpenAICompatibleProvider:
    provider_key = provider_name.lower()
    if provider_key not in configs:
        raise ValueError(f"Unsupported provider '{provider_name}'.")
    return OpenAICompatibleProvider(configs[provider_key])


