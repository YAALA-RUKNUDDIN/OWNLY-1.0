"""Storage provider factory — selected by STORAGE_PROVIDER env var.
S3 import is lazy so local dev doesn't require boto3."""
from functools import lru_cache

from app.core.config import settings
from app.core.errors import StorageError
from app.integrations.storage.base import StorageProvider


@lru_cache
def get_storage() -> StorageProvider:
    if settings.STORAGE_PROVIDER == "s3":
        try:
            from app.integrations.storage.s3 import S3StorageProvider
        except ImportError as e:
            raise StorageError(
                "S3 storage requested but boto3 is not installed. "
                "'pip install boto3' or set STORAGE_PROVIDER=local.",
                details={"error": str(e)},
            )
        return S3StorageProvider()
    from app.integrations.storage.local import LocalStorageProvider
    return LocalStorageProvider()