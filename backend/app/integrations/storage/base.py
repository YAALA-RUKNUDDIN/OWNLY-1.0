"""Storage provider abstraction.

Implementations:
  - LocalStorageProvider: dev/filesystem (private dir, authenticated short-lived URLs)
  - S3StorageProvider:    AWS S3 / Cloudflare R2 / MinIO via presigned URLs
"""
from abc import ABC, abstractmethod


class StorageProvider(ABC):
    @abstractmethod
    def upload(self, key: str, data: bytes, content_type: str) -> None:
        """Store bytes under a private key."""

    @abstractmethod
    def delete(self, key: str) -> None:
        """Permanently remove the object."""

    @abstractmethod
    def signed_url(self, key: str, expires_in_seconds: int = 600) -> str:
        """Return a short-lived, access-controlled download URL."""

    @abstractmethod
    def get(self, key: str) -> bytes:
        """Read object bytes (used for streaming through the API if needed)."""