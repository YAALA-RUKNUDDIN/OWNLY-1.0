"""Push provider factory — selected by PUSH_PROVIDER env var."""
from functools import lru_cache

from app.core.config import settings
from app.integrations.push.base import PushProvider


@lru_cache
def get_push() -> PushProvider:
    if settings.PUSH_PROVIDER == "fcm" and (settings.FCM_CREDENTIALS_PATH or settings.FCM_CREDENTIALS_JSON):
        from app.integrations.push.fcm import FCMProvider
        return FCMProvider(
            credentials_path=settings.FCM_CREDENTIALS_PATH or None,
            credentials_json=settings.FCM_CREDENTIALS_JSON or None,
        )
    from app.integrations.push.noop import NoopPushProvider
    return NoopPushProvider()