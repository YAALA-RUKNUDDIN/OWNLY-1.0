"""Push notification provider abstraction."""
from abc import ABC, abstractmethod


class PushProvider(ABC):
    name: str = "base"

    @abstractmethod
    def send(self, fcm_tokens: list[str], title: str, body: str, data: dict | None = None) -> list[str]:
        """Send to the given device tokens. Returns list of invalid tokens
        (so the caller can prune them)."""