"""Push notification & device registration tests (Phase 5)."""
import uuid
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

from app.models import DeviceToken, NotificationCategory, NotificationLog, Product, Warranty
from app.workers.jobs import run_daily_scan


def _user_id(client, headers):
    return client.get("/api/v1/auth/me", headers=headers).json()["id"]


class TestDeviceTokenAPI:
    def test_register_device_token(self, client, auth_headers, db_session):
        headers, _ = auth_headers
        token = "fcm_token_test_1234567890"

        resp = client.post(
            "/api/v1/users/me/devices",
            json={"fcm_token": token, "platform": "android"},
            headers=headers,
        )
        assert resp.status_code == 201
        assert resp.json() == {"message": "Device registered."}

        # Idempotent re-registration returns already registered
        resp2 = client.post(
            "/api/v1/users/me/devices",
            json={"fcm_token": token, "platform": "android"},
            headers=headers,
        )
        assert resp2.status_code == 201
        assert resp2.json() == {"message": "Device already registered."}

    def test_reassign_token_to_new_user(self, client, auth_headers, db_session):
        headers1, _ = auth_headers
        # Register a second user
        resp = client.post("/api/v1/auth/register", json={
            "name": "User Two",
            "email": "user2_devices@example.com",
            "password": "Password123!",
        })
        assert resp.status_code == 201
        token2 = resp.json()["tokens"]["access_token"]
        headers2 = {"Authorization": f"Bearer {token2}"}

        shared_device_token = "shared_phone_fcm_token_123456"

        # Register on user 1
        r1 = client.post(
            "/api/v1/users/me/devices",
            json={"fcm_token": shared_device_token, "platform": "ios"},
            headers=headers1,
        )
        assert r1.status_code == 201

        # Register same device on user 2 -> reassigns
        r2 = client.post(
            "/api/v1/users/me/devices",
            json={"fcm_token": shared_device_token, "platform": "ios"},
            headers=headers2,
        )
        assert r2.status_code == 201
        assert r2.json() == {"message": "Device re-assigned."}

        # Verify in DB that token belongs to user 2
        uid2 = _user_id(client, headers2)
        dev = db_session.query(DeviceToken).filter_by(fcm_token=shared_device_token).first()
        assert str(dev.user_id) == str(uid2)

    def test_unregister_device_token(self, client, auth_headers, db_session):
        headers, _ = auth_headers
        token = "token_to_delete_9876543210"

        client.post(
            "/api/v1/users/me/devices",
            json={"fcm_token": token, "platform": "android"},
            headers=headers,
        )
        assert db_session.query(DeviceToken).filter_by(fcm_token=token).count() == 1

        # Unregister
        del_resp = client.delete(f"/api/v1/users/me/devices/{token}", headers=headers)
        assert del_resp.status_code == 204

        assert db_session.query(DeviceToken).filter_by(fcm_token=token).count() == 0

        # Unregistering nonexistent token is safe and idempotent (204)
        del_resp2 = client.delete(f"/api/v1/users/me/devices/{token}", headers=headers)
        assert del_resp2.status_code == 204


class TestTestNotificationAPI:
    def test_send_test_notification_no_devices(self, client, auth_headers):
        headers, _ = auth_headers
        resp = client.post(
            "/api/v1/notifications/test",
            json={"title": "Hello", "body": "Testing 123", "route": "/reminders"},
            headers=headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["recipient_count"] == 0
        assert data["route"] == "/reminders"
        assert data["deep_link"] == "ownly:///reminders"

    def test_send_test_notification_with_registered_device(self, client, auth_headers):
        headers, _ = auth_headers
        token = "test_fcm_receiver_token_999"

        client.post(
            "/api/v1/users/me/devices",
            json={"fcm_token": token, "platform": "android"},
            headers=headers,
        )

        with patch("app.api.notifications.get_push") as mock_get_push:
            mock_provider = MagicMock()
            mock_provider.send.return_value = []
            mock_get_push.return_value = mock_provider

            resp = client.post(
                "/api/v1/notifications/test",
                json={
                    "title": "Warranty Alert",
                    "body": "Your item warranty is expiring",
                    "route": "/products/123",
                    "deep_link": "ownly:///products/123",
                },
                headers=headers,
            )
            assert resp.status_code == 200
            data = resp.json()
            assert data["recipient_count"] == 1
            assert token in data["tokens"]
            assert data["route"] == "/products/123"
            assert data["deep_link"] == "ownly:///products/123"

            # Check provider was called with correct data payload
            mock_provider.send.assert_called_once()
            call_args = mock_provider.send.call_args
            assert call_args[0][0] == [token]
            assert call_args[0][1] == "Warranty Alert"
            assert call_args[0][2] == "Your item warranty is expiring"
            payload = call_args[0][3]
            assert payload["route"] == "/products/123"
            assert payload["deep_link"] == "ownly:///products/123"
            assert payload["subject_type"] == "test"


class TestWorkerPayloadEnrichment:
    def test_daily_scan_delivers_deep_link_payload(self, client, auth_headers, db_session):
        headers, _ = auth_headers
        uid = uuid.UUID(_user_id(client, headers))
        token = "worker_test_token_111222333"

        client.post(
            "/api/v1/users/me/devices",
            json={"fcm_token": token, "platform": "android"},
            headers=headers,
        )

        today = datetime.now().date()
        p = Product(
            user_id=uid,
            name="Test Drone",
            category="electronics",
            purchase_date=today,
        )
        db_session.add(p)
        db_session.flush()

        w = Warranty(
            product_id=p.id,
            provider="DroneCare",
            warranty_type="manufacturer",
            start_date=today,
            end_date=today,  # 0 days remaining!
        )
        db_session.add(w)
        db_session.commit()

        with patch("app.workers.jobs.get_push") as mock_get_push:
            mock_provider = MagicMock()
            mock_provider.send.return_value = []
            mock_get_push.return_value = mock_provider

            stats = run_daily_scan()
            assert stats["warranty"] >= 1

            mock_provider.send.assert_called()
            # Find the call for this product
            found = False
            for call in mock_provider.send.call_args_list:
                tokens, title, body, data = call[0]
                if data.get("product_id") == str(p.id):
                    found = True
                    assert data["route"] == f"/products/{p.id}"
                    assert data["deep_link"] == f"ownly:///products/{p.id}"
                    assert data["subject_type"] == "warranty"
                    assert token in tokens
            assert found, "Expected push call with deep link payload for product"
