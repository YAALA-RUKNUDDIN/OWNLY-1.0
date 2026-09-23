"""OWNLY API — application factory and entrypoint."""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from starlette.requests import Request

from app.api import (
    admin, auth, documents, files, households, notifications, ocr, products, repairs,
    reminders, subscriptions, timeline, users, warranties,
)
from app.core.config import settings
from app.core.errors import AppError, register_error_handlers
from app.core.database import Base, engine
from app.integrations.monitoring import init_sentry

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
logger = logging.getLogger("ownly")

limiter = Limiter(key_func=get_remote_address, default_limits=[])


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create tables on startup if missing (Alembic is the source of truth in prod;
    # this keeps dev + test bootstrapping simple and reliable).
    from app import models  # noqa: F401 — ensure models are registered
    Base.metadata.create_all(bind=engine)
    logger.info("OWNLY backend ready (env=%s)", settings.ENVIRONMENT)
    yield


def create_app() -> FastAPI:
    init_sentry()  # no-op unless SENTRY_DSN is configured
    app = FastAPI(
        title=f"{settings.APP_NAME} API",
        version="1.0.0",
        description="Post-purchase ownership management platform.",
        lifespan=lifespan,
    )
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_handler)

    register_error_handlers(app)

    api_prefix = "/api/v1"
    app.include_router(auth.router, prefix=api_prefix)
    app.include_router(households.router, prefix=api_prefix)
    app.include_router(products.router, prefix=api_prefix)
    app.include_router(warranties.router, prefix=api_prefix)
    app.include_router(documents.router, prefix=api_prefix)
    app.include_router(reminders.router, prefix=api_prefix)
    app.include_router(timeline.router, prefix=api_prefix)
    app.include_router(repairs.router, prefix=api_prefix)
    app.include_router(users.router, prefix=api_prefix)
    app.include_router(ocr.router, prefix=api_prefix)
    app.include_router(files.router, prefix=api_prefix)
    app.include_router(admin.router, prefix=api_prefix)
    app.include_router(subscriptions.router, prefix=api_prefix)
    app.include_router(notifications.router, prefix=api_prefix)

    from app.api.dashboard import alias_router as today_alias_router
    from app.api.dashboard import router as dashboard_router
    app.include_router(dashboard_router, prefix=api_prefix)
    app.include_router(today_alias_router, prefix=api_prefix)

    @app.get("/health", tags=["health"])
    def health():
        return {"status": "ok", "app": settings.APP_NAME}

    return app


def _rate_limit_handler(request: Request, exc: RateLimitExceeded):
    from app.core.errors import error_response
    return error_response(429, "rate_limited", f"Rate limit exceeded: {exc.detail}")


app = create_app()
