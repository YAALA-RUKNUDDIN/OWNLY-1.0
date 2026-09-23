"""Dashboard, timeline, reminders, documents, OCR and worker tests."""
from datetime import date, datetime, timedelta

from app.workers.jobs import run_daily_scan


def _mk_product(client, headers, **kw):
    purchase = kw.get("purchase_date", datetime(2026, 1, 10, 9, 0))
    payload = {
        "name": kw.get("name", "MacBook Pro"),
        "category": kw.get("category", "laptops"),
        "purchase_date": purchase.isoformat() if isinstance(purchase, datetime) else purchase,
        "return_days": kw.get("return_days", 0),
    }
    resp = client.post("/api/v1/products", json=payload, headers=headers)
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


class TestDashboard:
    def test_empty_dashboard(self, client, auth_headers):
        headers, _ = auth_headers
        resp = client.get("/api/v1/dashboard/today", headers=headers)
        assert resp.status_code == 200
        body = resp.json()
        assert body["stats"]["total_products"] == 0
        assert body["attention"] == []
        assert body["greeting"]

    def test_expiring_warranty_in_attention(self, client, auth_headers):
        headers, _ = auth_headers
        soon = datetime.now() + timedelta(days=10)
        pid = _mk_product(client, headers, purchase_date=soon - timedelta(days=355))
        client.post(f"/api/v1/products/{pid}/warranty", json={
            "warranty_type": "manufacturer", "start_date": (soon - timedelta(days=355)).isoformat(),
            "duration_months": 12,
        }, headers=headers)
        body = client.get("/api/v1/dashboard/today", headers=headers).json()
        assert any(a["kind"] == "warranty_expiring" for a in body["attention"])
        assert body["stats"]["expiring_warranties"] >= 1


class TestTimeline:
    def test_product_creation_records_event(self, client, auth_headers):
        headers, _ = auth_headers
        pid = _mk_product(client, headers)
        events = client.get(f"/api/v1/products/{pid}/timeline", headers=headers).json()["events"]
        assert events[0]["event_type"] == "product_added"

    def test_timeline_isolation(self, client, auth_headers, second_auth_headers):
        headers_a, _ = auth_headers
        headers_b, _ = second_auth_headers
        pid = _mk_product(client, headers_a)
        assert client.get(f"/api/v1/products/{pid}/timeline", headers=headers_b).status_code == 404


class TestReminders:
    def test_create_complete_reminder(self, client, auth_headers):
        headers, _ = auth_headers
        pid = _mk_product(client, headers)
        r = client.post("/api/v1/reminders", json={
            "title": "Clean air filter", "reminder_type": "service_due",
            "scheduled_date": (date.today() + timedelta(days=5)).isoformat(),
            "product_id": pid,
        }, headers=headers)
        assert r.status_code == 201, r.text
        rid = r.json()["id"]
        done = client.patch(f"/api/v1/reminders/{rid}", json={"status": "completed"}, headers=headers)
        assert done.status_code == 200
        assert done.json()["status"] == "completed"

    def test_reminder_isolation(self, client, auth_headers, second_auth_headers):
        headers_a, _ = auth_headers
        headers_b, _ = second_auth_headers
        r = client.post("/api/v1/reminders", json={
            "title": "Private", "scheduled_date": date.today().isoformat(),
        }, headers=headers_a)
        rid = r.json()["id"]
        assert client.patch(f"/api/v1/reminders/{rid}", json={"status": "dismissed"}, headers=headers_b).status_code == 404


class TestServiceAndRepairs:
    def test_service_record_creates_next_reminder(self, client, auth_headers):
        headers, _ = auth_headers
        pid = _mk_product(client, headers, category="vehicles", name="Honda City")
        rec = client.post(f"/api/v1/products/{pid}/service-records", json={
            "service_date": date.today().isoformat(), "recurrence_months": 6, "provider": "Honda Service",
        }, headers=headers)
        assert rec.status_code == 201, rec.text
        assert rec.json()["next_service_date"] is not None
        reminders = client.get("/api/v1/reminders", params={"status": "upcoming"}, headers=headers).json()
        assert any(r["reminder_type"] == "service_due" for r in reminders)
        timeline = client.get(f"/api/v1/products/{pid}/timeline", headers=headers).json()
        assert any(e["event_type"] == "service_completed" for e in timeline["events"])

    def test_repair_records_timeline(self, client, auth_headers):
        headers, _ = auth_headers
        pid = _mk_product(client, headers)
        rep = client.post(f"/api/v1/products/{pid}/repairs", json={
            "repair_date": date.today().isoformat(), "description": "Screen replacement",
            "provider": "iStore", "cost": 250.0,
        }, headers=headers)
        assert rep.status_code == 201, rep.text
        timeline = client.get(f"/api/v1/products/{pid}/timeline", headers=headers).json()
        assert any(e["event_type"] == "repair_recorded" for e in timeline["events"])


class TestDocuments:
    def test_upload_download_delete_pdf(self, client, auth_headers):
        headers, _ = auth_headers
        pid = _mk_product(client, headers)
        pdf_bytes = b"%PDF-1.4 fake invoice content"
        up = client.post(
            f"/api/v1/products/{pid}/documents",
            files={"file": ("invoice.pdf", pdf_bytes, "application/pdf")},
            data={"document_name": "Invoice Jan", "document_type": "invoice"},
            headers=headers,
        )
        assert up.status_code == 201, up.text
        doc = up.json()
        assert doc["mime_type"] == "application/pdf"

        dl = client.get(f"/api/v1/documents/{doc['id']}/download", headers=headers)
        assert dl.status_code == 200
        assert dl.json()["download_url"]

        # Follow the signed URL (local storage → API-relative path)
        signed = client.get(dl.json()["download_url"])
        assert signed.status_code == 200
        assert signed.content == pdf_bytes

        assert client.delete(f"/api/v1/documents/{doc['id']}", headers=headers).status_code == 204

    def test_reject_disallowed_type(self, client, auth_headers):
        headers, _ = auth_headers
        pid = _mk_product(client, headers)
        up = client.post(
            f"/api/v1/products/{pid}/documents",
            files={"file": ("script.exe", b"MZ fake", "application/octet-stream")},
            data={"document_name": "bad", "document_type": "other"},
            headers=headers,
        )
        assert up.status_code == 422

    def test_document_isolation(self, client, auth_headers, second_auth_headers):
        headers_a, _ = auth_headers
        headers_b, _ = second_auth_headers
        pid = _mk_product(client, headers_a)
        up = client.post(
            f"/api/v1/products/{pid}/documents",
            files={"file": ("a.pdf", b"%PDF-1.4 secret", "application/pdf")},
            data={"document_name": "secret.pdf", "document_type": "invoice"},
            headers=headers_a,
        )
        doc_id = up.json()["id"]
        assert client.get(f"/api/v1/documents/{doc_id}/download", headers=headers_b).status_code == 404
        assert client.delete(f"/api/v1/documents/{doc_id}", headers=headers_b).status_code == 404


class TestDataOwnership:
    def test_export_and_delete_account(self, client):
        import uuid as _uuid
        email = f"export_{_uuid.uuid4().hex[:6]}@example.com"
        reg = client.post("/api/v1/auth/register", json={"name": "E", "email": email, "password": "password123"})
        headers = {"Authorization": f"Bearer {reg.json()['tokens']['access_token']}"}
        _mk_product(client, headers, name="Exported Laptop")

        export = client.get("/api/v1/users/me/export", headers=headers)
        assert export.status_code == 200
        assert export.json()["products"][0]["name"] == "Exported Laptop"

        assert client.delete("/api/v1/users/me", headers=headers).status_code == 204
        assert client.get("/api/v1/auth/me", headers=headers).status_code == 401


class TestDailyWorker:
    def test_worker_idempotent(self, client, auth_headers):
        headers, _ = auth_headers
        # Warranty expiring exactly in 7 days → "7d" milestone fires today
        end = datetime.now() + timedelta(days=7)
        pid = _mk_product(client, headers, purchase_date=end - timedelta(days=365))
        client.post(f"/api/v1/products/{pid}/warranty", json={
            "warranty_type": "manufacturer", "start_date": (end - timedelta(days=365)).isoformat(),
            "duration_months": 12,
        }, headers=headers)

        s1 = run_daily_scan()
        assert s1["warranty"] >= 1
        s2 = run_daily_scan()
        assert s2["warranty"] == 0  # duplicate prevented — never spam


class TestOCR:
    def test_ocr_rejects_non_image(self, client, auth_headers):
        headers, _ = auth_headers
        up = client.post(
            "/api/v1/ocr/extract",
            files={"file": ("doc.pdf", b"%PDF-1.4", "application/pdf")},
            headers=headers,
        )
        assert up.status_code == 422

    def test_admin_stats_access_control(self, client, auth_headers):
        headers, _ = auth_headers
        assert client.get("/api/v1/admin/stats", headers=headers).status_code == 403