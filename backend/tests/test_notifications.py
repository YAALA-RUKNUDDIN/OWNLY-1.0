"""Notification history endpoint (Phase 2): the user-visible record of
everything OWNLY has already told them."""
import uuid
from datetime import date, datetime, timedelta

from app.models import NotificationCategory, NotificationLog
from app.workers.jobs import run_daily_scan


def _user_id(client, headers):
    return client.get("/api/v1/auth/me", headers=headers).json()["id"]


def _seed(db_session, user_id, **kw):
    row = NotificationLog(
        user_id=uuid.UUID(str(user_id)),
        subject_type=kw.get("subject_type", "warranty"),
        subject_id=kw.get("subject_id", uuid.uuid4()),
        milestone=kw.get("milestone", "7d"),
        due_date=kw.get("due_date", date(2026, 6, 1)),
        category=kw.get("category", NotificationCategory.warranty),
        title=kw.get("title", "Warranty expiring"),
        body=kw.get("body", "Your warranty expires in 7 days."),
        delivery_status=kw.get("delivery_status", "sent"),
    )
    if kw.get("sent_at") is not None:
        row.sent_at = kw["sent_at"]
    db_session.add(row)
    db_session.commit()
    return row


def _mk_product(client, headers, **kw):
    purchase = kw.get("purchase_date", datetime(2026, 1, 10, 9, 0))
    resp = client.post("/api/v1/products", json={
        "name": kw.get("name", "MacBook Pro"),
        "category": kw.get("category", "laptops"),
        "purchase_date": purchase.isoformat() if isinstance(purchase, datetime) else purchase,
        "return_days": kw.get("return_days", 0),
    }, headers=headers)
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


class TestNotificationHistory:
    def test_empty_history(self, client, auth_headers):
        headers, _ = auth_headers
        resp = client.get("/api/v1/notifications", headers=headers)
        assert resp.status_code == 200, resp.text
        assert resp.json() == {"items": [], "total": 0, "page": 1, "page_size": 20}

    def test_history_is_newest_first_and_paginated(self, client, auth_headers, db_session):
        headers, _ = auth_headers
        uid = _user_id(client, headers)
        base = datetime(2026, 5, 1, 8, 0)
        for i in range(3):
            _seed(db_session, uid, milestone=f"{i}d", sent_at=base + timedelta(days=i))

        page1 = client.get("/api/v1/notifications?page=1&page_size=2", headers=headers).json()
        assert page1["total"] == 3
        assert len(page1["items"]) == 2
        assert page1["items"][0]["milestone"] == "2d"   # newest first
        assert page1["items"][1]["milestone"] == "1d"

        page2 = client.get("/api/v1/notifications?page=2&page_size=2", headers=headers).json()
        assert len(page2["items"]) == 1
        assert page2["items"][0]["milestone"] == "0d"

    def test_item_shape(self, client, auth_headers, db_session):
        headers, _ = auth_headers
        uid = _user_id(client, headers)
        row = _seed(db_session, uid, category=NotificationCategory.return_window,
                    subject_type="return", milestone="1d", title="Return window closes tomorrow",
                    delivery_status="sent")

        item = client.get("/api/v1/notifications", headers=headers).json()["items"][0]
        assert item["id"] == str(row.id)
        assert item["category"] == "return_window"
        assert item["subject_type"] == "return"
        assert item["title"] == "Return window closes tomorrow"
        assert item["due_date"].startswith("2026-06-01")

    def test_category_filter(self, client, auth_headers, db_session):
        headers, _ = auth_headers
        uid = _user_id(client, headers)
        _seed(db_session, uid, category=NotificationCategory.warranty)
        _seed(db_session, uid, category=NotificationCategory.service, subject_type="service")

        body = client.get("/api/v1/notifications?category=service", headers=headers).json()
        assert body["total"] == 1
        assert body["items"][0]["category"] == "service"

    def test_unknown_category_rejected(self, client, auth_headers):
        headers, _ = auth_headers
        resp = client.get("/api/v1/notifications?category=spam", headers=headers)
        assert resp.status_code == 422
        assert resp.json()["error"]["code"] == "validation_error"

    def test_subject_type_filter(self, client, auth_headers, db_session):
        headers, _ = auth_headers
        uid = _user_id(client, headers)
        _seed(db_session, uid, subject_type="warranty")
        _seed(db_session, uid, subject_type="reminder", category=NotificationCategory.custom)

        body = client.get("/api/v1/notifications?subject_type=reminder", headers=headers).json()
        assert body["total"] == 1
        assert body["items"][0]["subject_type"] == "reminder"

    def test_user_isolation(self, client, auth_headers, second_auth_headers, db_session):
        headers_a, _ = auth_headers
        headers_b, _ = second_auth_headers
        _seed(db_session, _user_id(client, headers_a))

        assert client.get("/api/v1/notifications", headers=headers_a).json()["total"] == 1
        assert client.get("/api/v1/notifications", headers=headers_b).json()["total"] == 0

    def test_export_includes_history(self, client, auth_headers, db_session):
        """Export covers the notification record as well."""
        headers, _ = auth_headers
        _seed(db_session, _user_id(client, headers), title="Included in export")
        export = client.get("/api/v1/users/me/export", headers=headers).json()
        assert export["notifications"][0]["title"] == "Included in export"

    def test_daily_scan_results_appear_in_history(self, client, auth_headers):
        """End-to-end: worker writes the log row → history endpoint serves it."""
        headers, _ = auth_headers
        end = datetime.now() + timedelta(days=7)
        pid = _mk_product(client, headers, purchase_date=end - timedelta(days=365))
        client.post(f"/api/v1/products/{pid}/warranty", json={
            "warranty_type": "manufacturer", "start_date": (end - timedelta(days=365)).isoformat(),
            "duration_months": 12,
        }, headers=headers)

        run_daily_scan()
        body = client.get("/api/v1/notifications", headers=headers).json()
        assert body["total"] >= 1
        item = body["items"][0]
        assert item["category"] == "warranty"
        assert item["milestone"] == "7d"
        assert item["subject_type"] == "warranty"
