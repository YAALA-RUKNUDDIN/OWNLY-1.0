"""Structured local logging provider — the default in development.

Emits one line per event through the standard logger so funnels are
observable locally (and greppable in container logs) without any network
dependency or PII beyond the internal user id.
"""
import json
import logging
import uuid

from app.integrations.analytics.base import AnalyticsProvider

logger = logging.getLogger("ownly.analytics")


class LogAnalyticsProvider(AnalyticsProvider):
    name = "log"

    def track(self, event: str, user_id: uuid.UUID | None = None, properties: dict | None = None) -> None:
        payload = {
            "event": event,
            "user_id": str(user_id) if user_id else None,
            "properties": properties or {},
        }
        logger.info("ANALYTICS %s", json.dumps(payload, default=str, sort_keys=True))
