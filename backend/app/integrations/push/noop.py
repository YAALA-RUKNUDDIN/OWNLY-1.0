"""No-op push provider for development (no FCM credentials configured).
Notifications are still logged to notification_log so the flow is testable."""
import logging

from app.integrations.push.base import PushProvider

logger = logging.getLogger("ownly.push")


class NoopPushProvider(PushProvider):
    name = "noop"

    def send(self, fcm_tokens: list[str], title: str, body: str, data: dict | None = None) -> list[str]:
        logger.info("PUSH (noop): %s | %s | tokens=%d", title, body, len(fcm_tokens))
        return []