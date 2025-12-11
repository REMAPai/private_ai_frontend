import os
from functools import lru_cache
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field


class ProviderConfig(BaseModel):
    name: str
    api_key: Optional[str] = None
    base_url: str = ""


class Settings(BaseModel):
    host: str = Field(default=os.environ.get("GATEWAY_HOST", "0.0.0.0"))
    port: int = Field(default=int(os.environ.get("GATEWAY_PORT", "9099")))
    database_url: str = Field(
        default=os.environ.get(
            "DATABASE_URL",
            f"sqlite:///{Path(__file__).resolve().parents[1] / 'data' / 'webui.db'}",
        )
    )
    default_provider: str = Field(
        default=os.environ.get("TOKEN_GATEWAY_DEFAULT_PROVIDER", "openai")
    )
    gateway_api_key: str = Field(
        default=os.environ.get("TOKEN_GATEWAY_API_KEY", "gateway-dev-key")
    )
    default_tokens_per_user: int = Field(
        default=int(os.environ.get("TOKEN_GATEWAY_DEFAULT_TOKENS", "100000"))
    )
    rate_limit_per_minute: int = Field(
        default=int(os.environ.get("TOKEN_GATEWAY_RATE_LIMIT_PER_MINUTE", "120"))
    )

    openai: ProviderConfig = ProviderConfig(
        name="openai",
        api_key=os.environ.get("OPENAI_API_KEY", ""),
        base_url=os.environ.get("OPENAI_API_BASE_URL", "https://api.openai.com/v1"),
    )
    anthropic: ProviderConfig = ProviderConfig(
        name="anthropic",
        api_key=os.environ.get("ANTHROPIC_API_KEY", ""),
        base_url=os.environ.get("ANTHROPIC_API_BASE_URL", "https://api.anthropic.com"),
    )
    gemini: ProviderConfig = ProviderConfig(
        name="gemini",
        api_key=os.environ.get("GEMINI_API_KEY", ""),
        base_url=os.environ.get(
            "GEMINI_API_BASE_URL", "https://generativelanguage.googleapis.com/v1beta"
        ),
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()


