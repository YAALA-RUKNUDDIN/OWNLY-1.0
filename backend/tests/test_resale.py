"""Test suite for Phase 10: Resale & Disposal Assistant, Valuation, Listing Generator & Portfolio Analytics."""
from datetime import date, datetime, timedelta, timezone
import pytest
from fastapi.testclient import TestClient

from app.models.repair import Repair


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _create_product(
    client,
    headers,
    name="MacBook Pro 16 M1 Max",
    brand="Apple",
    category="laptops",
    price=2000.0,
    condition="excellent",
    purchase_date=None,
):
    p_date = purchase_date or (utcnow() - timedelta(days=730)).isoformat()
    resp = client.post(
        "/api/v1/products",
        json={
            "name": name,
            "brand": brand,
            "model_number": "A2485",
            "serial_number": "C02G1234MD6R",
            "category": category,
            "condition": condition,
            "purchase_date": p_date,
            "purchase_price": price,
            "seller": "Apple Store",
            "notes": "Comes with original charger and box.",
        },
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


def test_calculate_valuation_depreciation(client: TestClient, auth_headers):
    """Verifies category depreciation curves and condition modifiers."""
    headers, _ = auth_headers
    prod_id = _create_product(client, headers, price=2000.0, condition="excellent")

    res = client.get(f"/api/v1/products/{prod_id}/valuation", headers=headers)
    assert res.status_code == 200
    data = res.json()

    assert data["product_id"] == prod_id
    assert data["product_name"] == "MacBook Pro 16 M1 Max"
    assert data["brand"] == "Apple"
    assert data["category"] == "laptops"
    assert data["condition"] == "excellent"
    assert data["purchase_price"] == 2000.0
    assert data["days_owned"] >= 729
    assert not data["is_sold"]

    # In laptops, 2 years old with excellent condition should retain approx 45-65%
    assert data["estimated_resale_value"] is not None
    assert 800.0 <= data["estimated_resale_value"] <= 1400.0
    assert data["value_retention_percent"] > 0
    assert data["suggested_listing_price_range"]["low"] < data["suggested_listing_price_range"]["fair"]
    assert data["suggested_listing_price_range"]["fair"] < data["suggested_listing_price_range"]["high"]
    assert data["cost_per_day"] > 0


def test_valuation_with_repairs(client: TestClient, db_session, auth_headers):
    """Repairs should increase Total Cost of Ownership."""
    headers, _ = auth_headers
    prod_id = _create_product(client, headers, price=2000.0)

    # Add repair record
    resp_rep = client.post(
        f"/api/v1/products/{prod_id}/repairs",
        json={
            "repair_date": date.today().isoformat(),
            "vendor": "Apple Store",
            "cost": 199.0,
            "description": "Battery replacement",
        },
        headers=headers,
    )
    assert resp_rep.status_code == 201

    res = client.get(f"/api/v1/products/{prod_id}/valuation", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["total_repairs_cost"] == 199.0
    # Net cost = 2000 + 199 - estimated_resale
    expected_net = 2000.0 + 199.0 - data["estimated_resale_value"]
    assert pytest.approx(data["net_cost_of_ownership"], 0.05) == expected_net


def test_update_product_condition(client: TestClient, auth_headers):
    """Updating condition should immediately update valuation."""
    headers, _ = auth_headers
    prod_id = _create_product(client, headers, price=1000.0, condition="good")

    # Mint condition should increase value
    res_mint = client.patch(f"/api/v1/products/{prod_id}/condition?condition=mint", headers=headers)
    assert res_mint.status_code == 200
    val_mint = res_mint.json()["estimated_resale_value"]

    # Poor condition should significantly reduce value
    res_poor = client.patch(f"/api/v1/products/{prod_id}/condition?condition=poor", headers=headers)
    assert res_poor.status_code == 200
    val_poor = res_poor.json()["estimated_resale_value"]

    assert val_mint > val_poor

    # Invalid condition should fail with 422/ValidationError
    res_bad = client.patch(f"/api/v1/products/{prod_id}/condition?condition=destroyed", headers=headers)
    assert res_bad.status_code in (400, 422)


def test_generate_resale_packet(client: TestClient, auth_headers):
    """Verifies generation of marketplace-ready Markdown & Plain Text listings with masked serials."""
    headers, _ = auth_headers
    prod_id = _create_product(client, headers)

    res = client.get(f"/api/v1/products/{prod_id}/resale-packet", headers=headers)
    assert res.status_code == 200
    packet = res.json()

    assert packet["product_id"] == prod_id
    assert "Apple MacBook Pro 16 M1 Max" in packet["title"]
    assert packet["specifications"]["serial_number_masked"].endswith("MD6R")
    assert packet["specifications"]["serial_number_masked"].startswith("****")

    # Formatted Markdown
    md = packet["formatted_markdown"]
    assert "# Apple MacBook Pro 16 M1 Max" in md
    assert "Asking Price:" in md
    assert "Item Specifications" in md
    assert "Proof of Purchase" in md

    # Plain text
    pt = packet["plain_text_description"]
    assert "Price:" in pt
    assert "Brand: Apple" in pt


def test_sell_product_flow_and_net_ownership(client: TestClient, auth_headers):
    """Selling a product records selling price, date, and timeline event, finalizing net ownership cost."""
    headers, _ = auth_headers
    prod_id = _create_product(client, headers, price=2000.0)

    sale_payload = {
        "resale_price": 1150.0,
        "resale_date": utcnow().isoformat(),
        "resale_platform": "eBay",
        "resale_notes": "Sold to verified buyer with expedited shipping.",
        "condition": "excellent",
    }

    res = client.post(f"/api/v1/products/{prod_id}/sell", json=sale_payload, headers=headers)
    assert res.status_code == 200
    data = res.json()

    assert data["is_sold"] is True
    assert data["actual_resale_price"] == 1150.0
    # Net cost = 2000 - 1150 = 850
    assert data["realized_net_cost"] == 850.0
    assert data["cost_per_day"] == round(850.0 / data["days_owned"], 2)

    # Verify timeline event was logged
    timeline_res = client.get(f"/api/v1/products/{prod_id}/timeline", headers=headers)
    assert timeline_res.status_code == 200
    events = timeline_res.json()["events"]
    assert any(e["event_type"] == "product_sold" and "1,150.00" in e["title"] for e in events)


def test_sell_future_date_rejected(client: TestClient, auth_headers):
    """Selling date cannot be in the future."""
    headers, _ = auth_headers
    prod_id = _create_product(client, headers)

    future_sale = {
        "resale_price": 1000.0,
        "resale_date": (utcnow() + timedelta(days=10)).isoformat(),
        "resale_platform": "Craigslist",
    }
    res = client.post(f"/api/v1/products/{prod_id}/sell", json=future_sale, headers=headers)
    assert res.status_code == 422


def test_dispose_product_flow(client: TestClient, auth_headers):
    """Disposing (recycling / donating) transitions status and emits timeline events."""
    headers, _ = auth_headers
    prod_id = _create_product(client, headers)

    disp_payload = {
        "disposal_type": "recycled",
        "disposal_date": utcnow().isoformat(),
        "notes": "Dropped off at certified e-waste recycling center.",
    }

    res = client.post(f"/api/v1/products/{prod_id}/dispose", json=disp_payload, headers=headers)
    assert res.status_code == 200

    # Verify timeline event
    timeline_res = client.get(f"/api/v1/products/{prod_id}/timeline", headers=headers)
    assert timeline_res.status_code == 200
    events = timeline_res.json()["events"]
    assert any(e["event_type"] == "product_recycled" for e in events)


def test_portfolio_analytics(client: TestClient, auth_headers):
    """Portfolio analytics aggregates active vs sold items, total purchase vs resale values, and categories."""
    headers, _ = auth_headers
    _create_product(client, headers, name="Product 1", price=1200.0, category="electronics")
    _create_product(client, headers, name="Product 2", price=800.0, category="furniture")

    res = client.get("/api/v1/portfolio/analytics", headers=headers)
    assert res.status_code == 200
    analytics = res.json()

    assert analytics["total_products_count"] >= 2
    assert analytics["total_purchase_value"] >= 2000.0
    assert analytics["total_estimated_resale_value"] > 0
    assert len(analytics["categories_breakdown"]) >= 2
    cats = [c["category"] for c in analytics["categories_breakdown"]]
    assert "electronics" in cats or "furniture" in cats


def test_household_viewer_rbac_cannot_sell_or_dispose(
    client: TestClient, auth_headers, second_auth_headers
):
    """A household member with 'viewer' role has read-only access and cannot sell or dispose."""
    owner_headers, _ = auth_headers
    viewer_headers, _ = second_auth_headers

    # 1. Owner creates a household
    hh_resp = client.post("/api/v1/households", json={"name": "Family Vault"}, headers=owner_headers)
    assert hh_resp.status_code == 201
    hh_id = hh_resp.json()["id"]

    # 2. Owner invites viewer
    inv_resp = client.post(f"/api/v1/households/{hh_id}/invites", json={"role": "viewer"}, headers=owner_headers)
    assert inv_resp.status_code == 201
    invite_code = inv_resp.json()["invite_code"]

    # 3. Viewer joins
    join_resp = client.post("/api/v1/households/join", json={"invite_code": invite_code}, headers=viewer_headers)
    assert join_resp.status_code == 200

    # 4. Owner creates product and shares with household
    prod_id = _create_product(client, owner_headers, name="Shared Espresso Maker", price=800.0)
    share_resp = client.post(f"/api/v1/products/{prod_id}/share", json={"household_id": hh_id}, headers=owner_headers)
    assert share_resp.status_code == 200

    # 5. Viewer can read valuation and resale packet
    val_res = client.get(f"/api/v1/products/{prod_id}/valuation", headers=viewer_headers)
    assert val_res.status_code == 200

    pkt_res = client.get(f"/api/v1/products/{prod_id}/resale-packet", headers=viewer_headers)
    assert pkt_res.status_code == 200

    # 6. Viewer cannot sell product
    sell_res = client.post(
        f"/api/v1/products/{prod_id}/sell",
        json={"resale_price": 500.0, "resale_platform": "Facebook"},
        headers=viewer_headers,
    )
    assert sell_res.status_code == 403

    # 7. Viewer cannot dispose product
    disp_res = client.post(
        f"/api/v1/products/{prod_id}/dispose",
        json={"disposal_type": "donated"},
        headers=viewer_headers,
    )
    assert disp_res.status_code == 403


def test_user_isolation(client: TestClient, auth_headers, second_auth_headers):
    """User B cannot view or modify valuation of User A's private product."""
    headers_a, _ = auth_headers
    headers_b, _ = second_auth_headers

    prod_id = _create_product(client, headers_a, name="Private Gold Watch", price=5000.0)

    val_res = client.get(f"/api/v1/products/{prod_id}/valuation", headers=headers_b)
    assert val_res.status_code == 404

    sell_res = client.post(
        f"/api/v1/products/{prod_id}/sell",
        json={"resale_price": 4000.0},
        headers=headers_b,
    )
    assert sell_res.status_code == 404
