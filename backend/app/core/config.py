"""Application configuration via environment variables (pydantic-settings)."""
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # App
    APP_NAME: str = "OWNLY"
    ENVIRONMENT: str = "development"
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000

    # Database
    DATABASE_URL: str = "postgresql+psycopg2://ownly:ownly_secret@localhost:5432/ownly"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # Security
    JWT_SECRET: str = "change-me-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 30

    # Storage
    STORAGE_PROVIDER: str = "local"  # local | s3
    STORAGE_LOCAL_PATH: str = "./storage_data"
    S3_ENDPOINT_URL: str = ""
    S3_BUCKET: str = "ownly-documents"
    S3_ACCESS_KEY_ID: str = ""
    S3_SECRET_ACCESS_KEY: str = ""
    S3_REGION: str = "auto"

    # OCR
    OCR_PROVIDER: str = "tesseract"  # tesseract | google_vision
    GOOGLE_VISION_API_KEY: str = ""
    TESSERACT_CMD: str = ""

    # Push
    PUSH_PROVIDER: str = "noop"  # noop | fcm
    FCM_CREDENTIALS_PATH: str = ""

    # Admin bootstrap
    ADMIN_EMAIL: str = "admin@ownly.local"
    ADMIN_PASSWORD: str = "change-me-admin"

    # Upload limits
    MAX_UPLOAD_SIZE_MB: int = 10
    ALLOWED_DOC_TYPES: str = "application/pdf,image/jpeg,image/png,image/heic,image/webp"

    @property
    def allowed_doc_types_list(self) -> list[str]:
        return [t.strip() for t in self.ALLOWED_DOC_TYPES.split(",") if t.strip()]

    @property
    def max_upload_bytes(self) -> int:
        return self.MAX_UPLOAD_SIZE_MB * 1024 * 1024

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT.lower() == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()