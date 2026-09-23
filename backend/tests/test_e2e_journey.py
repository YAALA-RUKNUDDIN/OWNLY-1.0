"""End-to-End User Journey Test (Phase 6).

Executes the complete OWNLY retention loop:
Signup
  ↓
Add Product
  ↓
Upload Receipt & Signed URL
  ↓
OCR Draft Processing (no auto-save)
  ↓
Confirm Product
  ↓
Create Warranty & Timeline
  ↓
Create Reminder
  ↓
TodayService Urgency Evaluation
  ↓
Device Token & Push Notification Dispatch
  ↓
Notification History
  ↓
Product Edit & Soft Deletion
  ↓
Subscription Gating
  ↓
Data Export
  ↓
Permanent Account Deletion (Cascade)
"""
import io
import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

from app.integrations.ocr.base import ExtractedFields
from app.models import Product


def test_complete_e2e_ownership_journey(client):
    # ── 1. User Signup & Auth ───────────────────────────────────────────────
    email = f"e2e_user_{uuid.uuid4().hex[:8]}@example.com"
    signup_resp = client.post(
        "/api/v1/auth/register",
        json={
            "name": "Alex Mercer",
            "email": email,
            "password": "Password123!",
        },
    )
    assert signup_resp.status_code == 201, signup_resp.text
    signup_data = signup_resp.json()
    token = signup_data["tokens"]["access_token"]
    refresh_token = signup_data["tokens"]["refresh_token"]
    user_id = signup_data["user"]["id"]
    headers = {"Authorization": f"Bearer {token}"}

    me_resp = client.get("/api/v1/auth/me", headers=headers)
    assert me_resp.status_code == 200
    assert me_resp.json()["email"] == email

    # ── 2. Add Product via Manual Entry ───────────────────────────────────────
    today = datetime.now(timezone.utc)
    product_resp = client.post(
        "/api/v1/products",
        json={
            "name": "Samsung Neo QLED 65",
            "brand": "Samsung",
            "category": "home_appliances",
            "model_number": "QN65QN90B",
            "serial_number": "SN-SAMS-998877",
            "purchase_date": today.isoformat(),
            "purchase_price": 1499.99,
            "currency": "USD",
            "seller": "Best Buy",
            "return_days": 15,
        },
        headers=headers,
    )
    assert product_resp.status_code == 201, product_resp.text
    prod1 = product_resp.json()
    prod1_id = prod1["id"]
    assert prod1["name"] == "Samsung Neo QLED 65"
    assert prod1["return_window"]["tracked"] is True
    assert prod1["return_window"]["days_remaining"] in (14, 15)

    # ── 3. Upload Receipt Document & Fetch Signed URL ────────────────────────
    receipt_bytes = b"%PDF-1.4 Mock Receipt for Samsung QLED TV"
    doc_resp = client.post(
        f"/api/v1/products/{prod1_id}/documents",
        files={"file": ("receipt.pdf", io.BytesIO(receipt_bytes), "application/pdf")},
        data={"document_type": "receipt", "document_name": "Samsung TV Receipt"},
        headers=headers,
    )
    assert doc_resp.status_code == 201, doc_resp.text
    doc_data = doc_resp.json()
    doc_id = doc_data["id"]
    assert doc_data["document_name"] == "Samsung TV Receipt"
    assert doc_data["document_type"] == "receipt"

    # Verify signed download URL
    dl_resp = client.get(f"/api/v1/documents/{doc_id}/download", headers=headers)
    assert dl_resp.status_code == 200
    dl_url = dl_resp.json()["download_url"]
    assert "token=" in dl_url or "expires=" in dl_url or "/api/v1/files/" in dl_url

    # ── 4. OCR Extraction: Returns Draft Without Auto-Saving ──────────────────
    ocr_image_bytes = b"GIF89a Fake Image Bytes with Invoice text"
    mock_provider = MagicMock()
    mock_provider.extract.return_value = ExtractedFields(
        product_name="Apple MacBook Pro 16",
        brand="Apple",
        model="A2485",
        price="2499.00",
        currency="USD",
        seller="Apple Store",
        confidence=0.95,
        raw_text="Apple Store Invoice #12345 MacBook Pro 16 $2499.00",
        provider="mock_tesseract",
    )
    with patch("app.api.ocr.get_ocr", return_value=mock_provider):
        ocr_resp = client.post(
            "/api/v1/ocr/extract",
            files={"file": ("invoice.png", io.BytesIO(ocr_image_bytes), "image/png")},
            headers=headers,
        )
    assert ocr_resp.status_code == 200, ocr_resp.text
    ocr_draft = ocr_resp.json()
    assert "draft" in ocr_draft
    assert ocr_draft["draft"]["product_name"] == "Apple MacBook Pro 16"
    assert "notice" in ocr_draft
    # CRITICAL: Verify OCR extracted a draft without persisting any product
    prod_list_before = client.get("/api/v1/products", headers=headers).json()
    assert prod_list_before["total"] == 1

    # ── 5. User Confirms OCR Draft & Creates Second Product ───────────────────
    prod2_resp = client.post(
        "/api/v1/products",
        json={
            "name": "Apple MacBook Pro 16",
            "brand": "Apple",
            "category": "laptops",
            "purchase_date": (today - timedelta(days=60)).isoformat(),
            "purchase_price": 2499.00,
            "return_days": 14,
        },
        headers=headers,
    )
    assert prod2_resp.status_code == 201
    prod2_id = prod2_resp.json()["id"]

    # ── 6. Create Warranty & Verify Timeline Events ───────────────────────────
    warranty_resp = client.post(
        f"/api/v1/products/{prod2_id}/warranty",
        json={
            "warranty_type": "manufacturer",
            "provider": "AppleCare+",
            "start_date": (today - timedelta(days=60)).isoformat(),
            "duration_months": 24,
        },
        headers=headers,
    )
    assert warranty_resp.status_code == 201
    w_data = warranty_resp.json()
    assert w_data["status"] == "active"
    assert w_data["provider"] == "AppleCare+"

    # Timeline has product_added and warranty_started
    timeline_resp = client.get(f"/api/v1/products/{prod2_id}/timeline", headers=headers)
    assert timeline_resp.status_code == 200
    events = [e["event_type"] for e in timeline_resp.json()["events"]]
    assert "product_added" in events
    assert "warranty_started" in events

    # ── 7. Create Reminder ───────────────────────────────────────────────────
    reminder_resp = client.post(
        "/api/v1/reminders",
        json={
            "title": "Clean dust filters",
            "description": "Quarterly appliance maintenance",
            "scheduled_date": (today + timedelta(days=30)).date().isoformat(),
            "product_id": prod1_id,
            "reminder_type": "service_due",
        },
        headers=headers,
    )
    assert reminder_resp.status_code == 201
    rem_id = reminder_resp.json()["id"]

    # ── 8. TodayService Urgency & Dashboard Evaluation ────────────────────────
    today_resp = client.get("/api/v1/dashboard/today", headers=headers)
    assert today_resp.status_code == 200
    dashboard = today_resp.json()
    assert dashboard["stats"]["total_products"] == 2
    assert dashboard["stats"]["active_warranties"] >= 1
    assert dashboard["stats"]["documents_stored"] >= 1

    # Verify alias /today
    today_alias = client.get("/api/v1/today", headers=headers)
    assert today_alias.status_code == 200
    assert today_alias.json()["stats"]["total_products"] == 2

    # ── 9. Device Token & Push Notification Dispatch ──────────────────────────
    device_token = "e2e_fcm_device_token_xyz_98765"
    reg_dev = client.post(
        "/api/v1/users/me/devices",
        json={"fcm_token": device_token, "platform": "android"},
        headers=headers,
    )
    assert reg_dev.status_code == 201

    # Send test notification with deep link
    test_push = client.post(
        "/api/v1/notifications/test",
        json={
            "title": "Warranty Notice",
            "body": "Your Samsung TV return window closes soon.",
            "route": f"/products/{prod1_id}",
            "deep_link": f"ownly:///products/{prod1_id}",
        },
        headers=headers,
    )
    assert test_push.status_code == 200
    assert test_push.json()["recipient_count"] == 1
    assert test_push.json()["route"] == f"/products/{prod1_id}"

    # ── 10. Notification History ─────────────────────────────────────────────
    hist_resp = client.get("/api/v1/notifications", headers=headers)
    assert hist_resp.status_code == 200
    history = hist_resp.json()
    assert history["total"] >= 1
    assert any("Samsung TV" in item["body"] for item in history["items"])

    # ── 11. Edit Product & Soft Deletion ──────────────────────────────────────
    patch_resp = client.patch(
        f"/api/v1/products/{prod1_id}",
        json={"notes": "Purchased with 5-year store warranty bundle"},
        headers=headers,
    )
    assert patch_resp.status_code == 200
    assert patch_resp.json()["notes"] == "Purchased with 5-year store warranty bundle"

    # Soft delete product 1
    del_prod = client.delete(f"/api/v1/products/{prod1_id}", headers=headers)
    assert del_prod.status_code == 204

    # Verify product 1 is no longer listed in active products
    list_after = client.get("/api/v1/products", headers=headers).json()
    assert list_after["total"] == 1
    assert list_after["items"][0]["id"] == prod2_id

    # ── 12. Subscription Tier Gating ──────────────────────────────────────────
    sub_resp = client.get("/api/v1/subscription", headers=headers)
    assert sub_resp.status_code == 200
    assert sub_resp.json()["tier"] == "free"
    assert sub_resp.json()["limits"]["max_products"] == 10

    # Upgrade to premium
    act_resp = client.post(
        "/api/v1/subscription/activate",
        json={"months": 12, "provider_ref": "promo_e2e"},
        headers=headers,
    )
    assert act_resp.status_code == 200
    assert act_resp.json()["tier"] == "premium"
    assert act_resp.json()["limits"]["max_products"] is None

    # ── 13. Data Privacy & Full Export ────────────────────────────────────────
    export_resp = client.get("/api/v1/users/me/export", headers=headers)
    assert export_resp.status_code == 200
    export_data = export_resp.json()
    assert export_data["profile"]["id"] == str(user_id)
    assert len(export_data["products"]) >= 1
    assert export_data["subscription"]["tier"] == "premium"
    assert len(export_data["notifications"]) >= 1

    # ── 14. Permanent Account Deletion & Cascading Cleanup ─────────────────────
    del_acc = client.delete("/api/v1/users/me", headers=headers)
    assert del_acc.status_code == 204

    # Subsequent access fails with 401 Unauthorized
    post_del_resp = client.get("/api/v1/auth/me", headers=headers)
    assert post_del_resp.status_code == 401


def test_security_audit_controls(client):
    """Verifies critical security invariants:
    - Strict cross-tenant isolation (User B receives 404 for User A's resources)
    - Signed URL expiration and cryptographic tampering prevention
    - Authentication boundary enforcement (401 without valid bearer token)
    """
    # Create User A
    user_a_email = f"user_a_{uuid.uuid4().hex[:8]}@example.com"
    r_a = client.post(
        "/api/v1/auth/register",
        json={"name": "User Alpha", "email": user_a_email, "password": "Password123!"},
    )
    headers_a = {"Authorization": f"Bearer {r_a.json()['tokens']['access_token']}"}

    # User A creates a product
    now = datetime.now(timezone.utc)
    prod_a = client.post(
        "/api/v1/products",
        json={
            "name": "Secret Enterprise Server",
            "category": "electronics",
            "purchase_date": now.isoformat(),
        },
        headers=headers_a,
    ).json()
    prod_a_id = prod_a["id"]

    # User A uploads a document
    doc_a = client.post(
        f"/api/v1/products/{prod_a_id}/documents",
        files={"file": ("invoice.pdf", io.BytesIO(b"%PDF-1.4 confidential invoice"), "application/pdf")},
        data={"document_type": "invoice", "document_name": "Confidential Invoice"},
        headers=headers_a,
    ).json()
    doc_a_id = doc_a["id"]

    # User A gets signed download URL
    dl_info = client.get(f"/api/v1/documents/{doc_a_id}/download", headers=headers_a).json()
    dl_url = dl_info["download_url"]

    # Verify normal download works
    file_resp = client.get(dl_url)
    assert file_resp.status_code == 200
    assert file_resp.content == b"%PDF-1.4 confidential invoice"

    # Security check: Tampered signature on download URL fails (401)
    tampered_url = dl_url[:-4] + "ffff"
    tampered_resp = client.get(tampered_url)
    assert tampered_resp.status_code == 401
    assert "Invalid signature" in tampered_resp.json()["error"]["message"]

    # Security check: Expired URL parameter fails (401)
    # Replace exp with past timestamp
    import re
    expired_url = re.sub(r"exp=\d+", "exp=1000000000", dl_url)
    expired_resp = client.get(expired_url)
    assert expired_resp.status_code == 401
    assert "expired" in expired_resp.json()["error"]["message"].lower()

    # Create User B
    user_b_email = f"user_b_{uuid.uuid4().hex[:8]}@example.com"
    r_b = client.post(
        "/api/v1/auth/register",
        json={"name": "User Beta", "email": user_b_email, "password": "Password123!"},
    )
    headers_b = {"Authorization": f"Bearer {r_b.json()['tokens']['access_token']}"}

    # Cross-tenant check 1: User B cannot view User A's product
    assert client.get(f"/api/v1/products/{prod_a_id}", headers=headers_b).status_code == 404

    # Cross-tenant check 2: User B cannot list User A's documents
    assert client.get(f"/api/v1/products/{prod_a_id}/documents", headers=headers_b).status_code == 404

    # Cross-tenant check 3: User B cannot get download URL for User A's document
    assert client.get(f"/api/v1/documents/{doc_a_id}/download", headers=headers_b).status_code == 404

    # Cross-tenant check 4: User B cannot delete User A's product
    assert client.delete(f"/api/v1/products/{prod_a_id}", headers=headers_b).status_code == 404

    # Authentication boundary check: Unauthenticated access gets 401
    assert client.get("/api/v1/products").status_code == 401
    assert client.get(f"/api/v1/products/{prod_a_id}").status_code == 401
    assert client.get("/api/v1/dashboard/today").status_code == 401
    assert client.get("/api/v1/users/me/export").status_code == 401
