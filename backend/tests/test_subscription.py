"""Subscription entitlements: plan limits, effective tier, quota gating,
and the subscription lifecycle endpoints (Phase 2)."""
from datetime import timedelta

from app.core.config import settings
from app.core.datetime_utils import utc_now
from app.models import PlanTier, Subscription, SubscriptionStatus
from app.services import subscription_service as svc


class TestPlanLimits:
    def test_free_limits(self):
        limits = svc.limits_for(PlanTier.free)
        assert limits.max_products == settings.FREE_PRODUCT_LIMIT
        assert "unlimited_products" not in limits.features

    def test_premium_limits(self):
        limits = svc.limits_for(PlanTier.premium)
        assert limits.max_products is None  # unlimited
        assert "unlimited_products" in limits.features


class TestEffectiveTier:
    def _sub(self, **kw):
        base = dict(tier=PlanTier.free, status=SubscriptionStatus.active, provider="none")
        base.update(kw)
        return Subscription(**base)

    def test_default_is_free(self):
        assert svc.effective_tier(self._sub()) is PlanTier.free

    def test_premium_with_future_expiry(self):
        sub = self._sub(tier=PlanTier.premium, expires_at=utc_now() + timedelta(days=10))
        assert svc.effective_tier(sub) is PlanTier.premium

    def test_premium_without_expiry_never_elapses(self):
        assert svc.effective_tier(self._sub(tier=PlanTier.premium)) is PlanTier.premium

    def test_elapsed_premium_reads_free(self):
        sub = self._sub(tier=PlanTier.premium, expires_at=utc_now() - timedelta(seconds=1))
        assert svc.effective_tier(sub) is PlanTier.free

    def test_naive_expiry_is_tolerated(self):
        # SQLite returns naive datetimes — must not raise (D-002).
        naive_future = utc_now().replace(tzinfo=None) + timedelta(days=5)
        sub = self._sub(tier=PlanTier.premium, expires_at=naive_future)
        assert svc.effective_tier(sub) is PlanTier.premium

    def test_expired_status_reads_free(self):
        sub = self._sub(tier=PlanTier.premium, status=SubscriptionStatus.expired)
        assert svc.effective_tier(sub) is PlanTier.free

    def test_canceled_but_entitled_reads_premium(self):
        sub = self._sub(tier=PlanTier.premium, status=SubscriptionStatus.canceled,
                        expires_at=utc_now() + timedelta(days=3))
        assert svc.effective_tier(sub) is PlanTier.premium


def _add_product(client, headers, name="Item"):
    return client.post(
        "/api/v1/products",
        json={"name": name, "category": "other", "purchase_date": "2026-01-01T00:00:00"},
        headers=headers,
    )


class TestSubscriptionAPI:
    def test_default_subscription_is_free(self, client, auth_headers):
        headers, _ = auth_headers
        resp = client.get("/api/v1/subscription", headers=headers)
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["tier"] == "free"
        assert body["status"] == "active"
        assert body["provider"] == "none"
        assert body["limits"]["max_products"] == settings.FREE_PRODUCT_LIMIT
        assert body["usage"]["products"] == 0

    def test_free_tier_product_cap_blocks_with_actionable_error(self, client, auth_headers, monkeypatch):
        monkeypatch.setattr(settings, "FREE_PRODUCT_LIMIT", 3)
        headers, _ = auth_headers
        for i in range(3):
            assert _add_product(client, headers, f"Item {i}").status_code == 201

        blocked = _add_product(client, headers, "Item 4")
        assert blocked.status_code == 403
        err = blocked.json()["error"]
        assert err["code"] == "plan_limit_reached"
        assert err["details"] == {"tier": "free", "limit": 3, "used": 3}

        body = client.get("/api/v1/subscription", headers=headers).json()
        assert body["usage"]["products"] == 3

    def test_soft_deleted_product_frees_quota(self, client, auth_headers, monkeypatch):
        monkeypatch.setattr(settings, "FREE_PRODUCT_LIMIT", 1)
        headers, _ = auth_headers
        first = _add_product(client, headers, "Only one")
        assert first.status_code == 201
        assert _add_product(client, headers, "Blocked").status_code == 403

        pid = first.json()["id"]
        assert client.delete(f"/api/v1/products/{pid}", headers=headers).status_code == 204
        assert _add_product(client, headers, "Now allowed").status_code == 201

    def test_premium_unlimited_products(self, client, auth_headers, monkeypatch):
        monkeypatch.setattr(settings, "FREE_PRODUCT_LIMIT", 2)
        headers, _ = auth_headers
        assert _add_product(client, headers, "A").status_code == 201
        assert _add_product(client, headers, "B").status_code == 201
        assert _add_product(client, headers, "C").status_code == 403

        activated = client.post("/api/v1/subscription/activate", json={"months": 6}, headers=headers)
        assert activated.status_code == 200, activated.text
        assert activated.json()["tier"] == "premium"
        assert activated.json()["limits"]["max_products"] is None

        for name in ("C", "D"):
            assert _add_product(client, headers, name).status_code == 201

    def test_cancel_keeps_entitlement_until_expiry(self, client, auth_headers):
        headers, _ = auth_headers
        client.post("/api/v1/subscription/activate", json={"months": 3}, headers=headers)
        canceled = client.post("/api/v1/subscription/cancel", headers=headers)
        assert canceled.status_code == 200, canceled.text
        body = canceled.json()
        assert body["status"] == "canceled"
        assert body["tier"] == "premium"  # still entitled until expires_at
        assert body["expires_at"] is not None

    def test_cancel_without_expiry_downgrades_immediately(self, client, auth_headers):
        headers, _ = auth_headers
        client.post("/api/v1/subscription/activate", json={"months": 0}, headers=headers)
        body = client.post("/api/v1/subscription/cancel", headers=headers).json()
        assert body["tier"] == "free"
        assert body["status"] == "expired"

    def test_subscription_is_per_user(self, client, auth_headers, second_auth_headers):
        headers_a, _ = auth_headers
        headers_b, _ = second_auth_headers
        client.post("/api/v1/subscription/activate", json={"months": 12}, headers=headers_a)

        assert client.get("/api/v1/subscription", headers=headers_a).json()["tier"] == "premium"
        other = client.get("/api/v1/subscription", headers=headers_b).json()
        assert other["tier"] == "free"
        assert other["usage"]["products"] == 0

    def test_invalid_activate_body_rejected(self, client, auth_headers):
        headers, _ = auth_headers
        resp = client.post("/api/v1/subscription/activate", json={"months": 9999}, headers=headers)
        assert resp.status_code == 422
        assert resp.json()["error"]["code"] == "validation_error"

    def test_export_includes_subscription(self, client, auth_headers):
        """Data export must cover entitlement too (users own their data)."""
        headers, _ = auth_headers
        client.post("/api/v1/subscription/activate", json={"months": 12}, headers=headers)
        export = client.get("/api/v1/users/me/export", headers=headers).json()
        assert export["subscription"]["tier"] == "premium"
        assert export["subscription"]["provider"] == "manual"
        assert export["notifications"] == []

    def test_account_deletion_removes_subscription(self, client):
        import uuid as _uuid
        email = f"subdel_{_uuid.uuid4().hex[:6]}@ownlymail.com"
        reg = client.post("/api/v1/auth/register",
                          json={"name": "D", "email": email, "password": "password123"})
        headers = {"Authorization": f"Bearer {reg.json()['tokens']['access_token']}"}
        client.post("/api/v1/subscription/activate", json={"months": 12}, headers=headers)

        assert client.delete("/api/v1/users/me", headers=headers).status_code == 204

        # A different account still starts free — no leaked entitlement.
        reg2 = client.post("/api/v1/auth/register",
                           json={"name": "D2", "email": f"n_{email}", "password": "password123"})
        headers2 = {"Authorization": f"Bearer {reg2.json()['tokens']['access_token']}"}
        assert client.get("/api/v1/subscription", headers=headers2).json()["tier"] == "free"
