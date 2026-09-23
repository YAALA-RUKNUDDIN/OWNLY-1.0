"""Warranty calculation + reminder + dashboard tests."""
from datetime import date, datetime, timedelta

from app.services.warranty_service import (
    compute_return_status,
    compute_warranty_status,
    resolve_end_date,
    warranty_milestones,
)


class TestWarrantyCalculations:
    def test_active_warranty(self):
        end = datetime.now() + timedelta(days=200)
        status, days = compute_warranty_status(end)
        assert status == "active"
        assert 190 <= days <= 200

    def test_expiring_soon(self):
        end = datetime.now() + timedelta(days=14)
        status, days = compute_warranty_status(end)
        assert status == "expiring_soon"
        assert days == 14

    def test_expired(self):
        end = datetime.now() - timedelta(days=1)
        status, days = compute_warranty_status(end)
        assert status == "expired"
        assert days == -1

    def test_boundary_exactly_30_days(self):
        end = datetime.now() + timedelta(days=30)
        assert compute_warranty_status(end)[0] == "expiring_soon"

    def test_boundary_exactly_31_days(self):
        end = datetime.now() + timedelta(days=31)
        assert compute_warranty_status(end)[0] == "active"


class TestReturnWindow:
    def test_not_tracked(self):
        assert compute_return_status(datetime.now(), 0)[0] == "none"

    def test_active_return(self):
        status, days, end = compute_return_status(datetime.now(), 30)
        assert status == "active"
        assert days == 30

    def test_expiring_return(self):
        purchase = datetime.now() - timedelta(days=27)
        status, days, end = compute_return_status(purchase, 30)
        assert status == "expiring_soon"
        assert days == 3

    def test_expired_return(self):
        purchase = datetime.now() - timedelta(days=40)
        assert compute_return_status(purchase, 30)[0] == "expired"


class TestMilestones:
    def test_milestones(self):
        today = date.today()
        assert warranty_milestones(today + timedelta(days=90), today) == ["90d"]
        assert warranty_milestones(today + timedelta(days=30), today) == ["30d"]
        assert warranty_milestones(today + timedelta(days=7), today) == ["7d"]
        assert warranty_milestones(today + timedelta(days=1), today) == ["1d"]
        assert warranty_milestones(today, today) == ["today"]
        assert warranty_milestones(today + timedelta(days=45), today) == []


class TestResolveEndDate:
    def test_explicit_end_date(self):
        end = datetime(2027, 6, 1)
        result = resolve_end_date(datetime(2026, 6, 1), end, None)
        # Contract: result is normalized to timezone-aware UTC (SQLite/PG parity).
        assert result.tzinfo is not None
        assert result.replace(tzinfo=None) == end

    def test_duration_months(self):
        result = resolve_end_date(datetime(2026, 1, 15), None, 12)
        assert result.date() == date(2027, 1, 15)
        assert result.tzinfo is not None

    def test_month_end_clamping(self):
        # Jan 31 + 1 month → Feb 28 (2026 not a leap year)
        result = resolve_end_date(datetime(2026, 1, 31), None, 1)
        assert result.date() == date(2026, 2, 28)
        assert result.tzinfo is not None

    def test_aware_input_is_preserved(self):
        from datetime import timezone
        start = datetime(2026, 6, 1, tzinfo=timezone.utc)
        result = resolve_end_date(start, None, 6)
        assert result.tzinfo is not None
        assert result.date() == date(2026, 12, 1)

    def test_requires_something(self):
        import pytest
        with pytest.raises(ValueError):
            resolve_end_date(datetime(2026, 1, 1), None, None)


class TestWarrantyAPI:
    def _create_product(self, client, headers):
        resp = client.post("/api/v1/products", json={
            "name": "iPhone 17", "category": "smartphones",
            "purchase_date": datetime(2026, 6, 1, 10, 0).isoformat(),
        }, headers=headers)
        return resp.json()["id"]

    def test_create_warranty_with_duration(self, client, auth_headers):
        headers, _ = auth_headers
        pid = self._create_product(client, headers)
        resp = client.post(f"/api/v1/products/{pid}/warranty", json={
            "warranty_type": "manufacturer", "start_date": datetime(2026, 6, 1).isoformat(),
            "duration_months": 12,
        }, headers=headers)
        assert resp.status_code == 201, resp.text
        assert resp.json()["end_date"].startswith("2027-06-01")

    def test_duplicate_warranty_conflict(self, client, auth_headers):
        headers, _ = auth_headers
        pid = self._create_product(client, headers)
        body = {"warranty_type": "manufacturer", "start_date": datetime(2026, 6, 1).isoformat(), "duration_months": 12}
        client.post(f"/api/v1/products/{pid}/warranty", json=body, headers=headers)
        dup = client.post(f"/api/v1/products/{pid}/warranty", json=body, headers=headers)
        assert dup.status_code == 409

    def test_extend_warranty_records_timeline(self, client, auth_headers):
        headers, _ = auth_headers
        pid = self._create_product(client, headers)
        w = client.post(f"/api/v1/products/{pid}/warranty", json={
            "warranty_type": "manufacturer", "start_date": datetime(2026, 6, 1).isoformat(), "duration_months": 12,
        }, headers=headers).json()
        ext = client.patch(f"/api/v1/warranties/{w['id']}", json={"duration_months": 24}, headers=headers)
        assert ext.status_code == 200
        assert ext.json()["end_date"].startswith("2028-06-01")
        timeline = client.get(f"/api/v1/products/{pid}/timeline", headers=headers).json()
        types = [e["event_type"] for e in timeline["events"]]
        assert "warranty_extended" in types
        assert "warranty_started" in types

    def test_warranty_isolation(self, client, auth_headers, second_auth_headers):
        headers_a, _ = auth_headers
        headers_b, _ = second_auth_headers
        pid = self._create_product(client, headers_a)
        w = client.post(f"/api/v1/products/{pid}/warranty", json={
            "warranty_type": "manufacturer", "start_date": datetime(2026, 6, 1).isoformat(), "duration_months": 12,
        }, headers=headers_a).json()
        assert client.patch(f"/api/v1/warranties/{w['id']}", json={"duration_months": 24}, headers=headers_b).status_code == 404