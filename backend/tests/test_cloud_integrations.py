"""Tests for Production Cloud Integrations (Phase 7).

Covers:
- AWS S3 / Cloudflare R2 / MinIO storage provider (S3StorageProvider)
- Google Cloud Vision OCR provider (GoogleVisionOCRProvider)
- Firebase Cloud Messaging provider (FCMProvider)
- Provider factories & error mapping
"""
import io
import json
from unittest.mock import MagicMock, patch

import pytest
from botocore.exceptions import ClientError

from app.core.errors import AppError, NotFoundError, OCRError, StorageError
from app.integrations.ocr.google_vision import GoogleVisionOCRProvider
from app.integrations.push.fcm import FCMProvider
from app.integrations.storage.s3 import S3StorageProvider


# ══════════════════════════════════════════════════════════════════════════════
# 1. AWS S3 / Cloudflare R2 / MinIO Storage Tests
# ══════════════════════════════════════════════════════════════════════════════

class TestS3StorageProvider:
    def test_s3_upload_and_get_success(self):
        mock_client = MagicMock()
        mock_client.get_object.return_value = {"Body": io.BytesIO(b"invoice-pdf-bytes")}

        provider = S3StorageProvider(client=mock_client, bucket="test-bucket")
        provider.upload("docs/inv1.pdf", b"invoice-pdf-bytes", "application/pdf")
        mock_client.put_object.assert_called_once_with(
            Bucket="test-bucket",
            Key="docs/inv1.pdf",
            Body=b"invoice-pdf-bytes",
            ContentType="application/pdf",
        )

        content = provider.get("docs/inv1.pdf")
        assert content == b"invoice-pdf-bytes"
        mock_client.get_object.assert_called_once_with(Bucket="test-bucket", Key="docs/inv1.pdf")

    def test_s3_get_not_found_mapped_to_not_found_error(self):
        mock_client = MagicMock()
        mock_client.get_object.side_effect = ClientError(
            {"Error": {"Code": "NoSuchKey", "Message": "The specified key does not exist."}},
            "GetObject",
        )
        provider = S3StorageProvider(client=mock_client, bucket="test-bucket")
        with pytest.raises(NotFoundError) as exc:
            provider.get("missing.pdf")
        assert "not found" in str(exc.value).lower()

    def test_s3_get_access_denied_mapped_to_storage_error(self):
        mock_client = MagicMock()
        mock_client.get_object.side_effect = ClientError(
            {"Error": {"Code": "AccessDenied", "Message": "Access Denied"}},
            "GetObject",
        )
        provider = S3StorageProvider(client=mock_client, bucket="test-bucket")
        with pytest.raises(StorageError) as exc:
            provider.get("forbidden.pdf")
        assert "access denied" in str(exc.value).lower()

    def test_s3_delete_success(self):
        mock_client = MagicMock()
        provider = S3StorageProvider(client=mock_client, bucket="test-bucket")
        provider.delete("docs/inv1.pdf")
        mock_client.delete_object.assert_called_once_with(Bucket="test-bucket", Key="docs/inv1.pdf")

    def test_s3_signed_url_generation(self):
        mock_client = MagicMock()
        mock_client.generate_presigned_url.return_value = "https://s3.amazonaws.com/test-bucket/docs/inv1.pdf?sig=abc"
        provider = S3StorageProvider(client=mock_client, bucket="test-bucket")

        url = provider.signed_url("docs/inv1.pdf", expires_in_seconds=900)
        assert "https://s3.amazonaws.com" in url
        mock_client.generate_presigned_url.assert_called_once_with(
            "get_object",
            Params={"Bucket": "test-bucket", "Key": "docs/inv1.pdf"},
            ExpiresIn=900,
        )

    def test_s3_missing_bucket_raises_storage_error(self):
        with pytest.raises(StorageError) as exc:
            S3StorageProvider(client=MagicMock(), bucket="")
        assert "S3_BUCKET is required" in str(exc.value)


# ══════════════════════════════════════════════════════════════════════════════
# 2. Google Cloud Vision OCR Tests
# ══════════════════════════════════════════════════════════════════════════════

class TestGoogleVisionOCR:
    def test_google_vision_extraction_with_api_key(self):
        raw_receipt_text = (
            "BEST BUY #1092\n"
            "123 Main Street\n"
            "Sony WH-1000XM5 Headphones\n"
            "Invoice #: BB-998811\n"
            "Date: 2026-08-15\n"
            "Subtotal: $349.99\n"
            "Tax: $28.00\n"
            "TOTAL: $377.99\n"
            "Thank you for shopping!\n"
        )
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "responses": [{
                "fullTextAnnotation": {"text": raw_receipt_text}
            }]
        }

        with patch("requests.post", return_value=mock_response) as mock_post:
            provider = GoogleVisionOCRProvider(api_key="test_google_api_key")
            fields = provider.extract(b"mock_image_bytes", "image/jpeg")

        # Verify endpoint called with API key
        mock_post.assert_called_once()
        call_url = mock_post.call_args[0][0]
        assert "key=test_google_api_key" in call_url

        # Verify parsed metadata
        assert fields.seller == "BEST BUY #1092"
        assert fields.product_name == "Sony WH-1000XM5 Headphones"
        assert fields.price == "377.99"
        assert fields.currency == "USD"
        assert fields.purchase_date == "2026-08-15"
        assert fields.invoice_number == "BB-998811"
        assert fields.confidence >= 0.85

    def test_google_vision_extraction_text_date_format(self):
        raw_receipt_text = (
            "Apple Store Fifth Avenue\n"
            "MacBook Air M3 15-inch\n"
            "Date: September 20, 2026\n"
            "Order: W123456789\n"
            "Amount Due: $1299.00\n"
        )
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "responses": [{"fullTextAnnotation": {"text": raw_receipt_text}}]
        }

        with patch("requests.post", return_value=mock_response):
            provider = GoogleVisionOCRProvider(api_key="mock_key")
            fields = provider.extract(b"image_bytes", "image/png")

        assert fields.purchase_date == "2026-09-20"
        assert fields.price == "1299.00"
        assert fields.seller == "Apple Store Fifth Avenue"
        assert fields.invoice_number == "W123456789"

    def test_google_vision_service_account_bearer_auth(self):
        mock_creds = MagicMock()
        mock_creds.valid = True
        mock_creds.token = "mock_oauth_bearer_token_xyz"

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "responses": [{"fullTextAnnotation": {"text": "Simple Store\nWidget\nTotal: $10.00"}}]
        }

        provider = GoogleVisionOCRProvider(api_key="")
        provider._oauth_creds = mock_creds

        with patch("requests.post", return_value=mock_response) as mock_post:
            fields = provider.extract(b"bytes", "image/jpeg")

        headers = mock_post.call_args[1]["headers"]
        assert headers["Authorization"] == "Bearer mock_oauth_bearer_token_xyz"
        assert fields.price == "10.00"

    def test_google_vision_api_error_response_raises_ocr_error(self):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "responses": [{
                "error": {"code": 3, "message": "Bad image data"}
            }]
        }

        with patch("requests.post", return_value=mock_response):
            provider = GoogleVisionOCRProvider(api_key="mock_key")
            with pytest.raises(OCRError) as exc:
                provider.extract(b"corrupt", "image/jpeg")
            assert "Bad image data" in str(exc.value)

    def test_google_vision_empty_annotation_raises_ocr_error(self):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"responses": [{}]}

        with patch("requests.post", return_value=mock_response):
            provider = GoogleVisionOCRProvider(api_key="mock_key")
            with pytest.raises(OCRError) as exc:
                provider.extract(b"blank", "image/jpeg")
            assert "No readable text" in str(exc.value)


# ══════════════════════════════════════════════════════════════════════════════
# 3. Firebase Cloud Messaging (FCM HTTP v1) Tests
# ══════════════════════════════════════════════════════════════════════════════

class TestFCMProvider:
    def test_fcm_send_success_and_token_caching(self):
        mock_creds = MagicMock()
        mock_creds.valid = True
        mock_creds.token = "oauth_token_12345"

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = '{"name": "projects/my-ownly-app/messages/msg_1"}'

        provider = FCMProvider(credentials=mock_creds, project_id="my-ownly-app")

        with patch("requests.post", return_value=mock_resp) as mock_post:
            invalid = provider.send(
                fcm_tokens=["device_token_abc"],
                title="Warranty Expiring",
                body="Your Sony TV warranty ends in 7 days.",
                data={"route": "/products/123", "product_id": "123"},
            )

        assert invalid == []
        mock_post.assert_called_once()
        url = mock_post.call_args[0][0]
        assert "projects/my-ownly-app/messages:send" in url

        payload = mock_post.call_args[1]["json"]["message"]
        assert payload["token"] == "device_token_abc"
        assert payload["notification"]["title"] == "Warranty Expiring"
        assert payload["data"]["route"] == "/products/123"
        assert payload["android"]["priority"] == "high"
        assert payload["android"]["notification"]["channel_id"] == "ownly_alerts"
        assert payload["apns"]["payload"]["aps"]["sound"] == "default"

        # Verify second send reuses valid cached token without calling refresh
        with patch("requests.post", return_value=mock_resp):
            provider.send(["token2"], "Title", "Body")
        mock_creds.refresh.assert_not_called()

    def test_fcm_unregistered_token_detected_for_cleanup(self):
        mock_creds = MagicMock()
        mock_creds.valid = True
        mock_creds.token = "oauth_token_12345"

        # FCM HTTP v1 returns 404 UNREGISTERED for uninstalled apps
        mock_resp = MagicMock()
        mock_resp.status_code = 404
        mock_resp.text = '{"error": {"code": 404, "message": "Requested entity was not found.", "status": "UNREGISTERED"}}'

        provider = FCMProvider(credentials=mock_creds, project_id="my-ownly-app")

        with patch("requests.post", return_value=mock_resp):
            invalid = provider.send(
                fcm_tokens=["stale_device_token_xyz"],
                title="Reminder",
                body="Service Due",
            )

        assert invalid == ["stale_device_token_xyz"]

    def test_fcm_init_from_json_string(self):
        fake_sa = {
            "type": "service_account",
            "project_id": "test-fcm-project",
            "private_key_id": "pk_123",
            "private_key": "-----BEGIN PRIVATE KEY-----\nMIIEvgIBADANBgkqhkiG9w0BAQEFAASCBKgwggSkAgEAAoIBAQC...\n-----END PRIVATE KEY-----\n",
            "client_email": "firebase-adminsdk@test-fcm-project.iam.gserviceaccount.com",
            "client_id": "112233",
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
        }
        with patch("google.oauth2.service_account.Credentials.from_service_account_info") as mock_from_info:
            mock_from_info.return_value = MagicMock()
            provider = FCMProvider(credentials_json=json.dumps(fake_sa))
            assert provider._project_id == "test-fcm-project"

    def test_fcm_missing_credentials_raises_app_error(self):
        with pytest.raises(AppError) as exc:
            FCMProvider(credentials_path="/nonexistent/path/fcm.json")
        assert "Failed to initialize FCM credentials" in str(exc.value)


# ══════════════════════════════════════════════════════════════════════════════
# 4. Provider Factory Tests
# ══════════════════════════════════════════════════════════════════════════════

def test_storage_factory_s3_switch():
    from app.integrations.storage import get_storage
    get_storage.cache_clear()
    with patch("app.core.config.settings.STORAGE_PROVIDER", "s3"):
        with patch("app.core.config.settings.S3_BUCKET", "my-bucket"):
            with patch("boto3.client") as mock_boto:
                mock_boto.return_value = MagicMock()
                storage = get_storage()
                assert isinstance(storage, S3StorageProvider)
    get_storage.cache_clear()


def test_ocr_factory_google_vision_switch():
    from app.integrations.ocr import get_ocr
    with patch("app.core.config.settings.OCR_PROVIDER", "google_vision"):
        ocr = get_ocr()
        assert isinstance(ocr, GoogleVisionOCRProvider)


def test_push_factory_fcm_switch():
    from app.integrations.push import get_push
    get_push.cache_clear()
    with patch("app.core.config.settings.PUSH_PROVIDER", "fcm"):
        with patch("app.core.config.settings.FCM_CREDENTIALS_JSON", '{"project_id": "test"}'):
            with patch("google.oauth2.service_account.Credentials.from_service_account_info"):
                push = get_push()
                assert isinstance(push, FCMProvider)
    get_push.cache_clear()
