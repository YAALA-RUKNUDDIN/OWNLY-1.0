"""Local filesystem storage (development). Files live in a private directory;
downloads are served through an authenticated, expiring token endpoint."""
import base64
import hashlib
import hmac
import os
import time
from pathlib import Path

from app.core.config import settings
from app.core.errors import NotFoundError, StorageError
from app.integrations.storage.base import StorageProvider


class LocalStorageProvider(StorageProvider):
    def __init__(self, base_path: str | None = None):
        self.base = Path(base_path or settings.STORAGE_LOCAL_PATH).resolve()
        self.base.mkdir(parents=True, exist_ok=True)

    def _path(self, key: str) -> Path:
        # Prevent path traversal
        p = (self.base / key).resolve()
        if not str(p).startswith(str(self.base)):
            raise StorageError("Invalid storage key")
        return p

    def upload(self, key: str, data: bytes, content_type: str) -> None:
        p = self._path(key)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(data)

    def delete(self, key: str) -> None:
        p = self._path(key)
        if p.exists():
            p.unlink()

    def get(self, key: str) -> bytes:
        p = self._path(key)
        if not p.exists():
            raise NotFoundError("File not found in storage")
        return p.read_bytes()

    def signed_url(self, key: str, expires_in_seconds: int = 600) -> str:
        exp = int(time.time()) + expires_in_seconds
        sig = hmac.new(
            settings.JWT_SECRET.encode(), f"{key}:{exp}".encode(), hashlib.sha256
        ).hexdigest()
        b64key = base64.urlsafe_b64encode(key.encode()).decode()
        return f"/api/v1/files/{b64key}?exp={exp}&sig={sig}"