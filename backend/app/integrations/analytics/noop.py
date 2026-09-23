"""No-op analytics provider (tests, and environments with no sink configured)."""
import logging
import uuid

from app.integrations.analytics.base import AnalyticsProvider

logger = logging.getLogger("ownly.analytics")


class NoopAnalyticsProvider(AnalyticsProvider):
    name = "noop"

    def track(self, event: str, user_id: uuid.UUID | None = None, properties: dict | None = None) -> None:
        logger.debug("ANALYTICS (noop): %s user=%s props=%s", event, user_id, properties)
