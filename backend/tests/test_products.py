"""Product CRUD + user isolation tests."""
import uuid
from datetime import datetime, timedelta


def _make_product_payload(**overrides):
    payload = {
        "name": "ThinkPad X1 Carbon",
        "brand": "Lenovo",
        "category": "laptops",
        "purchase_date": datetime(2026, 1, 15, 12, 0).isoformat(),
        "purchase_price": 1499.99,
        "currency": "USD",
        "seller": "Amazon",
        "return_days": 30,
    }
    payload.update(overrides)
    return payload


def test_create_and_get_product(client, auth_headers):
    headers, _ = auth_headers
    created = client.post("/api/v1/products", json=_make_product_payload(), headers=headers)
    assert created.status_code == 201, created.text
    product = created.json()
    assert product["name"] == "ThinkPad X1 Carbon"
    assert product["warranty"]["status"] == "none"
    assert product["return_window"]["tracked"] is True

    fetched = client.get(f"/api/v1/products/{product['id']}", headers=headers)
    assert fetched.status_code == 200
    assert fetched.json()["id"] == product["id"]


def test_product_validation_error(client, auth_headers):
    headers, _ = auth_headers
    bad = _make_product_payload(name="")
    resp = client.post("/api/v1/products", json=bad, headers=headers)
    assert resp.status_code == 422
    assert resp.json()["error"]["code"] == "validation_error"


def test_pagination_and_search(client, auth_headers):
    headers, _ = auth_headers
    for i in range(3):
        client.post("/api/v1/products", json=_make_product_payload(name=f"Phone {i}", category="smartphones"), headers=headers)
    resp = client.get("/api/v1/products", params={"page": 1, "page_size": 2}, headers=headers)
    assert resp.status_code == 200
    assert len(resp.json()["items"]) <= 2
    assert resp.json()["total"] >= 3

    search = client.get("/api/v1/products", params={"search": "Phone 1"}, headers=headers)
    assert search.status_code == 200
    assert any(p["name"] == "Phone 1" for p in search.json()["items"])


def test_user_isolation_cannot_access_others_product(client, auth_headers, second_auth_headers):
    """User A creates a product; User B must get 404 for it."""
    headers_a, _ = auth_headers
    headers_b, _ = second_auth_headers
    created = client.post("/api/v1/products", json=_make_product_payload(), headers=headers_a)
    pid = created.json()["id"]

    assert client.get(f"/api/v1/products/{pid}", headers=headers_b).status_code == 404
    assert client.patch(f"/api/v1/products/{pid}", json={"name": "Hacked"}, headers=headers_b).status_code == 404
    assert client.delete(f"/api/v1/products/{pid}", headers=headers_b).status_code == 404


def test_update_and_soft_delete(client, auth_headers):
    headers, _ = auth_headers
    created = client.post("/api/v1/products", json=_make_product_payload(), headers=headers)
    pid = created.json()["id"]

    updated = client.patch(f"/api/v1/products/{pid}", json={"status": "sold"}, headers=headers)
    assert updated.status_code == 200
    assert updated.json()["status"] == "sold"

    deleted = client.delete(f"/api/v1/products/{pid}", headers=headers)
    assert deleted.status_code == 204
    assert client.get(f"/api/v1/products/{pid}", headers=headers).status_code == 404


def test_unauthenticated_access_denied(client):
    assert client.get("/api/v1/products").status_code == 401