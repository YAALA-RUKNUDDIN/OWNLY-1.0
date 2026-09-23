"""Analytics provider abstraction.

Mirrors the OCR/storage/push integration layout: a tiny ABC, concrete
providers, and a settings-selected factory. `track()` is the only function
call sites should use — it never raises, so analytics can never break a
request (worst case the event is dropped and logged).
"""
from abc import ABC, abstractmethod
import uuid


class AnalyticsProvider(ABC):
    name: str = "base"

    @abstractmethod
    def track(self, event: str, user_id: uuid.UUID | None = None, properties: dict | None = None) -> None:
        """Record a single event. Implementations must not raise."""
