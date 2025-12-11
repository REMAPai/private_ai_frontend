import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from token_gateway.config import get_settings
from token_gateway.routes import router
from token_gateway.utils import SimpleRateLimiter

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="Token Gateway",
        version="0.1.0",
        description="OpenAI-compatible gateway for quota and rate limiting",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.state.settings = settings
    app.state.rate_limiter = SimpleRateLimiter(settings.rate_limit_per_minute)

    app.include_router(router)
    return app


app = create_app()


