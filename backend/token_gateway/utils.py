import asyncio
import logging
import time
from collections import defaultdict, deque
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple

import tiktoken
from fastapi import HTTPException
from sqlalchemy.orm import Session, joinedload

from token_gateway.config import Settings
from open_webui.models.subscriptions import Client, SubscriptionPlan, UsagePerUser
from open_webui.models.users import Users

logger = logging.getLogger(__name__)


class SimpleRateLimiter:
    def __init__(self, limit: int, window_seconds: int = 60):
        self.limit = limit
        self.window = window_seconds
        self._requests: Dict[str, deque] = defaultdict(deque)
        self._lock = asyncio.Lock()

    async def check(self, key: str) -> Tuple[bool, Optional[float]]:
        async with self._lock:
            now = time.time()
            dq = self._requests[key]
            while dq and dq[0] <= now - self.window:
                dq.popleft()
            if len(dq) >= self.limit:
                retry_after = self.window - (now - dq[0])
                return False, max(retry_after, 0.0)
            dq.append(now)
            return True, None


def get_user_from_headers(headers: Dict[str, str], session: Optional[Session] = None) -> str:
    """
    Extract user_id from headers and validate it exists in the User table.
    Returns the user.id from the User table to ensure we're using the correct user_id.
    """
    user_id_from_header = (
        headers.get("X-OpenWebUI-User-Id")
        or headers.get("X-User-Id")
        or None
    )
    
    if not user_id_from_header:
        return "anonymous"
    
    # Validate that the user_id exists in the User table
    # This ensures we're using the actual user.id from the User table, not just any ID
    try:
        user = Users.get_user_by_id(user_id_from_header)
        if user and user.id:
            # Return the validated user.id from the User table
            logger.debug(f"Validated user_id from header: {user_id_from_header} -> {user.id}")
            return user.id
        else:
            logger.warning(f"User ID from header not found in User table: {user_id_from_header}")
            return "anonymous"
    except Exception as e:
        logger.error(f"Error validating user_id from header {user_id_from_header}: {e}")
        return "anonymous"


def estimate_tokens_from_messages(messages, model: str) -> int:
    try:
        enc = tiktoken.encoding_for_model(model)
    except Exception:
        enc = tiktoken.get_encoding("cl100k_base")

    total = 0
    for message in messages:
        for value in message.values():
            if isinstance(value, str):
                total += len(enc.encode(value))
            elif isinstance(value, list):
                for item in value:
                    if isinstance(item, str):
                        total += len(enc.encode(item))
                    elif isinstance(item, dict):
                        total += sum(len(enc.encode(str(v))) for v in item.values())
            elif isinstance(value, dict):
                total += sum(len(enc.encode(str(v))) for v in value.values())
    return total


def estimate_tokens_from_prompt(payload: dict) -> int:
    if "messages" in payload:
        model = payload.get("model", "gpt-4o-mini")
        return estimate_tokens_from_messages(payload["messages"], model)
    if "input" in payload:
        model = payload.get("model", "text-embedding-3-small")
        if isinstance(payload["input"], list):
            return sum(
                estimate_tokens_from_messages([{"role": "user", "content": item} if isinstance(item, str) else item], model)
                if isinstance(item, dict)
                else len(tiktoken.get_encoding("cl100k_base").encode(str(item)))
                for item in payload["input"]
            )
        return len(tiktoken.get_encoding("cl100k_base").encode(str(payload["input"])))
    return 0


def _reset_window_if_needed(client: Client, session: Session):
    now = datetime.utcnow()
    if client and client.next_reset_date and client.next_reset_date < now:
        client.next_reset_date = now + timedelta(days=30)
        for usage in client.users:
            usage.used_tokens = 0
        session.commit()


def resolve_limits(
    session: Session, user_id: str, settings: Settings
) -> Tuple[int, UsagePerUser, Optional[Client], Optional[SubscriptionPlan]]:
    """
    Resolve token limits for a user.
    
    Args:
        session: Database session
        user_id: The user.id from the User table (validated via get_user_from_headers)
        settings: Gateway settings
        
    Returns:
        Tuple of (allowed_tokens, UsagePerUser record, Client, SubscriptionPlan)
    """
    # Query UsagePerUser by user_id (which references user.id from User table)
    usage = (
        session.query(UsagePerUser)
        .filter(UsagePerUser.user_id == user_id)
        .options(joinedload(UsagePerUser.client).joinedload(Client.subscription_plan))
        .first()
    )

    client = usage.client if usage else None
    plan = client.subscription_plan if client else None
    if client:
        _reset_window_if_needed(client, session)

    allowed = settings.default_tokens_per_user
    if plan and plan.is_active:
        seats = max(client.seats_purchased if client else 1, 1)
        allowed = plan.tokens_per_seat * seats

    if not usage:
        # Create new UsagePerUser record with user_id from User table
        # user_id must be the user.id from the User table (validated via get_user_from_headers)
        usage = UsagePerUser(user_id=user_id, used_tokens=0, client_id=client.id if client else None)
        session.add(usage)
        session.commit()
        session.refresh(usage)
        logger.info(f"Created new UsagePerUser record for user_id: {user_id}")

    return allowed, usage, client, plan


def enforce_quota(
    session: Session,
    user_id: str,
    estimated_tokens: int,
    settings: Settings,
) -> None:
    allowed, usage, client, plan = resolve_limits(session, user_id, settings)

    if usage.used_tokens + estimated_tokens > allowed:
        # Create a detailed error message with quota information
        remaining = max(0, allowed - usage.used_tokens)
        error_detail = (
            f"Token quota exceeded. You have used {usage.used_tokens:,} of {allowed:,} tokens. "
            f"Remaining: {remaining:,} tokens. This request requires approximately {estimated_tokens:,} tokens."
        )
        if plan and plan.plan_name:
            error_detail += f" Your current plan: {plan.plan_name}."
        
        raise HTTPException(
            status_code=429,
            detail=error_detail,
            headers={
                "X-Tokens-Allowed": str(allowed),
                "X-Tokens-Used": str(usage.used_tokens),
                "X-Tokens-Remaining": str(remaining),
                "X-Tokens-Requested": str(estimated_tokens),
            },
        )


def record_usage(session: Session, usage: UsagePerUser, tokens_used: int):
    """
    Record token usage for a user.
    
    Args:
        session: Database session
        usage: UsagePerUser record (contains user_id which references user.id from User table)
        tokens_used: Number of tokens used
    """
    usage.used_tokens += max(tokens_used, 0)
    usage.updated_at = datetime.utcnow()
    session.commit()
    logger.debug(f"Recorded {tokens_used} tokens for user_id: {usage.user_id}, total: {usage.used_tokens}")


