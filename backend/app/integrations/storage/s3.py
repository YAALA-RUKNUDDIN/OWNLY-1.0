"""S3-compatible storage: AWS S3, Cloudflare R2, MinIO. Private bucket,
access only via presigned GET URLs."""
from typing import Any

import boto3
from botocore.client import Config
from botocore.exceptions import BotoCoreError, ClientError

from app.core.config import settings
from app.core.errors import NotFoundError, StorageError
from app.integrations.storage.base import StorageProvider


class S3StorageProvider(StorageProvider):
    def __init__(self, client: Any = None, bucket: str | None = None):
        self.bucket = bucket if bucket is not None else settings.S3_BUCKET
        if not self.bucket:
            raise StorageError("S3_BUCKET is required when using S3 storage provider.")

        if client is not None:
            self.client = client
        else:
            s3_config_args: dict[str, Any] = {
                "signature_version": settings.S3_SIGNATURE_VERSION or "s3v4"
            }
            if settings.S3_FORCE_PATH_STYLE:
                s3_config_args["s3"] = {"addressing_style": "path"}

            self.client = boto3.client(
                "s3",
                endpoint_url=settings.S3_ENDPOINT_URL or None,
                aws_access_key_id=settings.S3_ACCESS_KEY_ID or None,
                aws_secret_access_key=settings.S3_SECRET_ACCESS_KEY or None,
                region_name=settings.S3_REGION if settings.S3_REGION != "auto" else None,
                config=Config(**s3_config_args),
            )

    def upload(self, key: str, data: bytes, content_type: str) -> None:
        try:
            self.client.put_object(
                Bucket=self.bucket,
                Key=key,
                Body=data,
                ContentType=content_type,
            )
        except ClientError as e:
            raise StorageError(f"Failed to upload object to S3: {e}", details={"error": str(e), "key": key})
        except BotoCoreError as e:
            raise StorageError(f"S3 connection error during upload: {e}", details={"error": str(e), "key": key})

    def delete(self, key: str) -> None:
        try:
            self.client.delete_object(Bucket=self.bucket, Key=key)
        except ClientError as e:
            raise StorageError(f"Failed to delete object from S3: {e}", details={"error": str(e), "key": key})
        except BotoCoreError as e:
            raise StorageError(f"S3 connection error during delete: {e}", details={"error": str(e), "key": key})

    def get(self, key: str) -> bytes:
        try:
            resp = self.client.get_object(Bucket=self.bucket, Key=key)
            return resp["Body"].read()
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "")
            if error_code in ("NoSuchKey", "404"):
                raise NotFoundError("File not found in storage", details={"key": key})
            raise StorageError(f"Failed to fetch object from S3: {e}", details={"error": str(e), "key": key})
        except BotoCoreError as e:
            raise StorageError(f"S3 connection error during get: {e}", details={"error": str(e), "key": key})

    def signed_url(self, key: str, expires_in_seconds: int = 600) -> str:
        try:
            return self.client.generate_presigned_url(
                "get_object",
                Params={"Bucket": self.bucket, "Key": key},
                ExpiresIn=expires_in_seconds,
            )
        except (ClientError, BotoCoreError) as e:
            raise StorageError(f"Failed to generate presigned S3 URL: {e}", details={"error": str(e), "key": key})