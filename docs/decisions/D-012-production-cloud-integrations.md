# D-012: Production Cloud Integrations — AWS S3/R2, Google Vision OCR & Firebase FCM

**Status:** Accepted · **Date:** 2026-09-24 · **Phase:** 7

## Context

OWNLY's core domain was architected with pluggable provider abstractions for Storage (`StorageProvider`), OCR (`OCRProvider`), and Push notifications (`PushProvider`). While Phase 1-6 established local fallback providers (private filesystem storage with HMAC tokens, Tesseract OCR, and noop push logger) to enable zero-dependency development and CI runs, production environments demand robust, resilient integrations with enterprise cloud backends:
1. **Object Storage:** Scalable cloud object storage supporting AWS S3, Cloudflare R2, and MinIO with presigned GET download URLs, path-style/virtual addressing support, and robust error translation.
2. **Receipt OCR:** Google Cloud Vision API with flexible authentication (supporting both API Key and OAuth2 service account / Application Default Credentials) and advanced multi-format receipt heuristics (dates, totals vs subtotals, and vendor extraction).
3. **Push Notifications:** Firebase Cloud Messaging (FCM HTTP v1) supporting 12-factor raw JSON service account credentials in environment variables, OAuth2 access token caching, native platform options (Android channel `ownly_alerts`, APNs sound and badge), and automatic stale token pruning.

## Decision

- **Object Storage (`S3StorageProvider` in `app/integrations/storage/s3.py`):**
  - Uses `boto3` and `botocore` client configured with `s3v4` signatures.
  - Implements `S3_FORCE_PATH_STYLE` configuration to ensure seamless compatibility with MinIO and custom S3-compatible object storage endpoints (e.g. Cloudflare R2).
  - Explicitly maps AWS `ClientError` and `BotoCoreError` into domain errors: `NoSuchKey` / 404 maps to `NotFoundError`, while permissions and connection issues map to `StorageError` with structured context.
  - Generates secure presigned GET download URLs with configurable expiration.

- **Receipt OCR (`GoogleVisionOCRProvider` in `app/integrations/ocr/google_vision.py`):**
  - **Dual Authentication Modes:**
    - API Key: `GOOGLE_VISION_API_KEY` attached to Vision API REST URL.
    - Service Account / ADC: Loads credentials from `GOOGLE_CREDENTIALS_JSON` (raw JSON string), `GOOGLE_APPLICATION_CREDENTIALS` (file path), or `google.auth.default()`, acquiring and caching OAuth2 bearer tokens.
  - **Advanced Receipt Parsing Heuristics:**
    - Merchant detection: identifies business name from header lines while filtering transaction boilerplate (`tel:`, `welcome`, `tax invoice`).
    - Multi-format date parsing: extracts dates across ISO (`YYYY-MM-DD`), slash (`MM/DD/YYYY` or `DD/MM/YYYY`), and textual formats (`Month DD, YYYY`).
    - Price/Total extraction: prioritizes bottom-line `TOTAL`, `AMOUNT DUE`, and `GRAND TOTAL` matches over subtotals and sales tax lines.
    - Confidence scoring: dynamic calculation based on field coverage and document structure.
  - Standardized error handling: maps Google Vision error response payloads and network failures into `OCRError`.

- **Push Notifications (`FCMProvider` in `app/integrations/push/fcm.py`):**
  - **12-Factor Secret Injection:** Supports both `FCM_CREDENTIALS_JSON` (raw service account JSON string, ideal for Docker/Kubernetes/ECS secrets) and `FCM_CREDENTIALS_PATH` (file path on disk).
  - **OAuth2 Token Caching:** Caches the acquired bearer token and checks `creds.valid` before dispatching requests, eliminating redundant OAuth token exchange round-trips on every push notification.
  - **Native Platform Envelopes:**
    - Android: `priority: "high"`, `channel_id: "ownly_alerts"`, `sound: "default"`.
    - iOS (APNs): `apns-priority: "10"`, `aps: {"sound": "default", "badge": 1}`.
  - **Stale Token Pruning:** Inspects FCM HTTP v1 error responses (`UNREGISTERED`, `INVALID_ARGUMENT`) and returns invalid tokens for automated database unregistration.

- **Provider Factory Refinement:**
  - `get_storage()`, `get_ocr()`, and `get_push()` inspect environment configuration cleanly with LRU caching, falling back gracefully to local dev implementations when cloud credentials are omitted.

## Consequences

- Production deployments can switch to AWS S3 / Cloudflare R2, Google Cloud Vision, and Firebase FCM by setting environment variables, with zero code changes.
- Developers and CI pipelines continue running with local SQLite, filesystem storage, and noop push without needing external cloud accounts or credentials.
- 126 backend tests and 18 mobile tests validate all operational paths with 100% green status.
