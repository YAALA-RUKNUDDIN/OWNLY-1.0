"""Analytics provider factory — selected by ANALYTICS_PROVIDER env var.

Call sites use `track()`: it resolves the provider once, swallows any error
(analytics is never allowed to fail a user request), and accepts both plain
strings and `AnalyticsEvent` members.
"""
import logging
import uuid
from functools import lru_cache

from app.core.analytics_events import AnalyticsEvent
from app.core.config import settings

logger = logging.getLogger("ownly.analytics")


@lru_cache
def get_analytics():
    if settings.ANALYTICS_PROVIDER == "noop":
        from app.integrations.analytics.noop import NoopAnalyticsProvider
        return NoopAnalyticsProvider()
    from app.integrations.analytics.log import LogAnalyticsProvider
    return LogAnalyticsProvider()


def track(
    event: str | AnalyticsEvent,
    user_id: uuid.UUID | None = None,
    properties: dict | None = None,
) -> None:
    """Fire-and-forget event. Never raises."""
    try:
        name = event.value if isinstance(event, AnalyticsEvent) else str(event)
        get_analytics().track(name, user_id=user_id, properties=properties)
    except Exception:  # pragma: no cover — defensive: analytics must never break requests
        logger.warning("Analytics event dropped: %s", event, exc_info=True)
