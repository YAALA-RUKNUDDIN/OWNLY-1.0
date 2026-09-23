"""Monitoring integrations (error tracking).

Sentry is optional at runtime: enabled purely by setting SENTRY_DSN, and it
degrades to a logged no-op when the SDK is not installed, so the backend
never hard-depends on it.
"""
import logging
from functools import lru_cache

from app.core.config import settings

logger = logging.getLogger("ownly.monitoring")


@lru_cache
def init_sentry() -> bool:
    """Initialize Sentry once per process. Returns True when active."""
    dsn = (settings.SENTRY_DSN or "").strip()
    if not dsn:
        logger.debug("Sentry disabled (SENTRY_DSN not set).")
        return False
    try:
        import sentry_sdk
        from sentry_sdk.integrations.fastapi import FastApiIntegration
        from sentry_sdk.integrations.starlette import StarletteIntegration
    except ImportError:
        logger.warning("SENTRY_DSN is set but sentry-sdk is not installed; error tracking is off.")
        return False

    sentry_sdk.init(
        dsn=dsn,
        environment=settings.ENVIRONMENT,
        release=f"{settings.APP_NAME.lower()}-backend",
        traces_sample_rate=settings.SENTRY_TRACES_SAMPLE_RATE,
        # Privacy-first product: never ship user data to a third party by default.
        send_default_pii=False,
        integrations=[StarletteIntegration(), FastApiIntegration()],
    )
    logger.info("Sentry initialized (env=%s, traces=%s)", settings.ENVIRONMENT, settings.SENTRY_TRACES_SAMPLE_RATE)
    return True
