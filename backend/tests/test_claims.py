"""Test suite for Phase 9: Warranty Claim Assistant, Brand Support Directory & Dossiers."""
from datetime import datetime, timezone
import pytest


def _create_product(client, headers, name="MacBook Pro 16", brand="Apple", price=2499.0):
    resp = client.post(
        "/api/v1/products",
        json={
            "name": name,
            "brand": brand,
            "model_number": "A2485",
            "serial_number": "C02G1234MD6R",
            "category": "laptops",
            "purchase_date": "2026-01-15T10:00:00Z",
            "purchase_price": price,
            "seller": "Apple Store Fifth Ave",
            "return_days": 14,
        },
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


def _add_warranty(client, headers, product_id, duration_months=12):
    resp = client.post(
        f"/api/v1/products/{product_id}/warranty",
        json={
            "warranty_type": "manufacturer",
            "start_date": "2026-01-15T10:00:00Z",
            "duration_months": duration_months,
            "provider": "AppleCare",
        },
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


class TestBrandSupportDirectory:
    def test_list_brand_support(self, client, auth_headers):
        headers, _ = auth_headers
        resp = client.get("/api/v1/claims/support-directory", headers=headers)
        assert resp.status_code == 200
        items = resp.json()
        assert len(items) >= 10
        brands = [b["brand"] for b in items]
        assert "Apple" in brands
        assert "Samsung" in brands
        assert "Dell" in brands
        assert "Sony" in brands

    def test_filter_by_category(self, client, auth_headers):
        headers, _ = auth_headers
        resp = client.get("/api/v1/claims/support-directory?category=audio", headers=headers)
        assert resp.status_code == 200
        items = resp.json()
        assert len(items) >= 1
        for item in items:
            assert "audio" in item["category"].lower() or "electronics" in item["category"].lower()

    def test_get_specific_brand(self, client, auth_headers):
        headers, _ = auth_headers
        resp = client.get("/api/v1/claims/support-directory/apple", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["brand"] == "Apple"
        assert "1-800" in data["support_phone"]
        assert "apple.com" in data["claim_portal_url"]

    def test_unknown_brand_404(self, client, auth_headers):
        headers, _ = auth_headers
        resp = client.get("/api/v1/claims/support-directory/nonexistent_brand_xyz", headers=headers)
        assert resp.status_code == 404
        assert resp.json()["error"]["code"] == "not_found"


class TestClaimLifecycleAndDossier:
    def test_file_and_get_claim(self, client, auth_headers):
        headers, _ = auth_headers
        pid = _create_product(client, headers, "MacBook Pro", "Apple")
        wid = _add_warranty(client, headers, pid)

        # File claim
        resp = client.post(
            f"/api/v1/products/{pid}/claims",
            json={
                "title": "Display Backlight Failure",
                "issue_description": "Horizontal lines appear across the bottom half of the Liquid Retina screen after wake.",
                "incident_date": "2026-09-20T14:30:00Z",
                "warranty_id": wid,
                "claim_reference": "APP-RMA-9042",
                "contact_phone": "555-0199",
            },
            headers=headers,
        )
        assert resp.status_code == 201, resp.text
        claim = resp.json()
        cid = claim["id"]
        assert claim["title"] == "Display Backlight Failure"
        assert claim["status"] == "draft"
        assert claim["claim_reference"] == "APP-RMA-9042"
        assert claim["product_name"] == "MacBook Pro"
        assert claim["brand_support"] is not None
        assert claim["brand_support"]["brand"] == "Apple"

        # Verify listed under product
        p_claims = client.get(f"/api/v1/products/{pid}/claims", headers=headers).json()
        assert len(p_claims) == 1
        assert p_claims[0]["id"] == cid

        # Verify listed in user claims
        u_claims = client.get("/api/v1/claims", headers=headers).json()
        assert u_claims["total"] >= 1
        assert any(c["id"] == cid for c in u_claims["items"])

        # Verify timeline event recorded
        timeline = client.get(f"/api/v1/products/{pid}/timeline", headers=headers).json()
        event_types = [e["event_type"] for e in timeline["events"]]
        assert "claim_filed" in event_types

    def test_future_incident_date_rejected(self, client, auth_headers):
        headers, _ = auth_headers
        pid = _create_product(client, headers)
        resp = client.post(
            f"/api/v1/products/{pid}/claims",
            json={
                "title": "Invalid Future Claim",
                "issue_description": "This hasn't happened yet.",
                "incident_date": "2099-01-01T00:00:00Z",
            },
            headers=headers,
        )
        assert resp.status_code == 422
        assert resp.json()["error"]["code"] == "validation_error"

    def test_update_claim_status_and_resolution(self, client, auth_headers):
        headers, _ = auth_headers
        pid = _create_product(client, headers, "Sony WH-1000XM5", "Sony")
        claim = client.post(
            f"/api/v1/products/{pid}/claims",
            json={
                "title": "ANC Hiss in Right Ear Cup",
                "issue_description": "High pitched buzzing when Active Noise Cancelling is enabled.",
                "incident_date": "2026-09-18T10:00:00Z",
            },
            headers=headers,
        ).json()
        cid = claim["id"]

        # Advance to in_review
        patch1 = client.patch(
            f"/api/v1/claims/{cid}",
            json={"status": "in_review", "claim_reference": "SONY-CASE-4910"},
            headers=headers,
        )
        assert patch1.status_code == 200
        assert patch1.json()["status"] == "in_review"
        assert patch1.json()["claim_reference"] == "SONY-CASE-4910"

        # Advance to approved and set resolution notes and covered cost
        patch2 = client.patch(
            f"/api/v1/claims/{cid}",
            json={
                "status": "approved",
                "resolution_notes": "Authorized warranty replacement unit dispatched via FedEx.",
                "claim_cost_covered": 399.99,
            },
            headers=headers,
        )
        assert patch2.status_code == 200
        assert patch2.json()["status"] == "approved"
        assert patch2.json()["claim_cost_covered"] == 399.99

        # Timeline has claim_updated and claim_resolved
        timeline = client.get(f"/api/v1/products/{pid}/timeline", headers=headers).json()
        types = [e["event_type"] for e in timeline["events"]]
        assert "claim_updated" in types
        assert "claim_resolved" in types

    def test_generate_claim_dossier(self, client, auth_headers):
        headers, _ = auth_headers
        pid = _create_product(client, headers, "Dell XPS 15", "Dell", 1899.0)
        _add_warranty(client, headers, pid)

        # Upload a dummy invoice document
        client.post(
            f"/api/v1/products/{pid}/documents",
            data={"document_name": "Dell Direct Invoice", "document_type": "invoice"},
            files={"file": ("invoice.pdf", b"%PDF-1.4 test invoice receipt content", "application/pdf")},
            headers=headers,
        )

        claim = client.post(
            f"/api/v1/products/{pid}/claims",
            json={
                "title": "Battery Swelling Trackpad Displaced",
                "issue_description": "Lithium-ion battery expanded, lifting trackpad out of chassis.",
                "incident_date": "2026-09-22T08:00:00Z",
                "claim_reference": "DELL-SR-8921",
                "contact_phone": "+1-555-432-1000",
            },
            headers=headers,
        ).json()
        cid = claim["id"]

        resp = client.get(f"/api/v1/claims/{cid}/dossier", headers=headers)
        assert resp.status_code == 200
        dossier = resp.json()

        assert dossier["dossier_id"] == cid
        assert dossier["product"]["name"] == "Dell XPS 15"
        assert dossier["product"]["brand"] == "Dell"
        assert dossier["warranty"] is not None
        assert len(dossier["documents"]) >= 1
        assert "download_url" in dossier["documents"][0]
        assert dossier["brand_support"]["brand"] == "Dell"
        assert dossier["claimant"]["email"] is not None

        # Formatted markdown verification
        md = dossier["formatted_markdown"]
        assert "# WARRANTY CLAIM DOSSIER" in md
        assert "Dell XPS 15" in md
        assert "Battery Swelling Trackpad Displaced" in md
        assert "DELL-SR-8921" in md
        assert "Dell Direct Invoice" in md

    def test_delete_claim(self, client, auth_headers):
        headers, _ = auth_headers
        pid = _create_product(client, headers)
        claim = client.post(
            f"/api/v1/products/{pid}/claims",
            json={
                "title": "Temporary Test Claim",
                "issue_description": "User filed by mistake.",
                "incident_date": "2026-09-21T00:00:00Z",
            },
            headers=headers,
        ).json()
        cid = claim["id"]

        del_resp = client.delete(f"/api/v1/claims/{cid}", headers=headers)
        assert del_resp.status_code == 204

        get_resp = client.get(f"/api/v1/claims/{cid}", headers=headers)
        assert get_resp.status_code == 404


class TestClaimSecurityAndRBAC:
    def test_claim_user_isolation(self, client):
        # Register User A
        r1 = client.post("/api/v1/auth/register", json={
            "name": "User A", "email": "claim_user_a@test.com", "password": "password123"
        })
        token_a = {"Authorization": f"Bearer {r1.json()['tokens']['access_token']}"}

        # Register User B
        r2 = client.post("/api/v1/auth/register", json={
            "name": "User B", "email": "claim_user_b@test.com", "password": "password123"
        })
        token_b = {"Authorization": f"Bearer {r2.json()['tokens']['access_token']}"}

        # User A creates product and claim
        pid = _create_product(client, token_a, "User A Phone", "Samsung")
        claim = client.post(
            f"/api/v1/products/{pid}/claims",
            json={"title": "Camera Artifacts", "issue_description": "Purple lines", "incident_date": "2026-09-20T00:00:00Z"},
            headers=token_a,
        ).json()
        cid = claim["id"]

        # User B cannot get, update, or delete User A's claim
        assert client.get(f"/api/v1/claims/{cid}", headers=token_b).status_code == 404
        assert client.patch(f"/api/v1/claims/{cid}", json={"title": "Hacked"}, headers=token_b).status_code == 404
        assert client.delete(f"/api/v1/claims/{cid}", headers=token_b).status_code == 404

    def test_household_rbac_viewer_blocked(self, client):
        # User Admin creates household
        r_admin = client.post("/api/v1/auth/register", json={
            "name": "Admin Owner", "email": "claim_admin@test.com", "password": "password123"
        })
        t_admin = {"Authorization": f"Bearer {r_admin.json()['tokens']['access_token']}"}

        hh = client.post("/api/v1/households", json={"name": "Family House"}, headers=t_admin).json()
        hid = hh["id"]

        # Admin shares product to household
        pid = _create_product(client, t_admin, "Living Room TV", "LG")
        client.post(f"/api/v1/products/{pid}/share", json={"household_id": hid}, headers=t_admin)

        # Admin generates viewer invite
        inv = client.post(f"/api/v1/households/{hid}/invites", json={"role": "viewer"}, headers=t_admin).json()
        code = inv["invite_code"]

        # User Viewer joins
        r_viewer = client.post("/api/v1/auth/register", json={
            "name": "Household Viewer", "email": "claim_viewer@test.com", "password": "password123"
        })
        t_viewer = {"Authorization": f"Bearer {r_viewer.json()['tokens']['access_token']}"}
        join_resp = client.post("/api/v1/households/join", json={"invite_code": code}, headers=t_viewer)
        assert join_resp.status_code == 200, join_resp.text

        # Viewer can see the shared product
        p_get = client.get(f"/api/v1/products/{pid}", headers=t_viewer)
        assert p_get.status_code == 200

        # Viewer attempts to file a claim -> 403 Forbidden!
        resp_file = client.post(
            f"/api/v1/products/{pid}/claims",
            json={"title": "Cracked Screen", "issue_description": "Accident", "incident_date": "2026-09-20T00:00:00Z"},
            headers=t_viewer,
        )
        assert resp_file.status_code == 403
        assert resp_file.json()["error"]["code"] == "forbidden"
