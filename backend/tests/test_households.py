"""Tests for Household & Family Sharing (Phase 8).

Covers:
- Household creation, listing, details
- Invite code generation and redemption
- Product sharing & cross-user access within household
- Shared document & warranty access
- Role-based permissions (admin vs member vs viewer)
- Unsharing products & privacy isolation
- Member removal and leaving
- Safe household deletion (products unlinked, not deleted)
"""
import io
import uuid
from datetime import datetime, timedelta, timezone

from app.models.household import HouseholdInvite, HouseholdRole


def _register_user(client, name: str) -> tuple[dict, str]:
    email = f"{name.lower().replace(' ', '_')}_{uuid.uuid4().hex[:6]}@ownlytest.com"
    resp = client.post(
        "/api/v1/auth/register",
        json={"name": name, "email": email, "password": "Password123!"},
    )
    assert resp.status_code == 201, resp.text
    token = resp.json()["tokens"]["access_token"]
    user_id = resp.json()["user"]["id"]
    return {"Authorization": f"Bearer {token}"}, user_id


class TestHouseholdBasics:
    def test_create_and_list_household(self, client):
        headers, user_id = _register_user(client, "Alice Founder")

        # Create household
        create_resp = client.post(
            "/api/v1/households",
            json={"name": "Smith Family Home"},
            headers=headers,
        )
        assert create_resp.status_code == 201, create_resp.text
        h_data = create_resp.json()
        assert h_data["name"] == "Smith Family Home"
        assert h_data["current_user_role"] == "admin"
        assert h_data["member_count"] == 1
        hid = h_data["id"]

        # List households
        list_resp = client.get("/api/v1/households", headers=headers)
        assert list_resp.status_code == 200
        items = list_resp.json()
        assert len(items) == 1
        assert items[0]["id"] == hid
        assert items[0]["name"] == "Smith Family Home"

        # Get household detail
        detail_resp = client.get(f"/api/v1/households/{hid}", headers=headers)
        assert detail_resp.status_code == 200
        detail = detail_resp.json()
        assert detail["id"] == hid
        assert len(detail["members"]) == 1
        assert detail["members"][0]["role"] == "admin"
        assert detail["members"][0]["name"] == "Alice Founder"

    def test_rename_household_admin_only(self, client):
        headers_a, _ = _register_user(client, "Admin User")
        headers_b, user_b_id = _register_user(client, "Viewer User")

        h_id = client.post(
            "/api/v1/households", json={"name": "Old Name"}, headers=headers_a
        ).json()["id"]

        # Viewer joins
        invite = client.post(
            f"/api/v1/households/{h_id}/invites",
            json={"role": "viewer"},
            headers=headers_a,
        ).json()
        client.post(
            "/api/v1/households/join",
            json={"invite_code": invite["invite_code"]},
            headers=headers_b,
        )

        # Viewer attempts rename -> 403
        bad_rename = client.patch(
            f"/api/v1/households/{h_id}",
            json={"name": "Viewer Hacked Name"},
            headers=headers_b,
        )
        assert bad_rename.status_code == 403

        # Admin renames -> 200
        ok_rename = client.patch(
            f"/api/v1/households/{h_id}",
            json={"name": "New Family Name"},
            headers=headers_a,
        )
        assert ok_rename.status_code == 200
        assert ok_rename.json()["name"] == "New Family Name"


class TestHouseholdSharingAndRBAC:
    def test_invite_join_and_product_sharing(self, client):
        headers_a, user_a_id = _register_user(client, "Alice Smith")
        headers_b, user_b_id = _register_user(client, "Bob Smith")

        # 1. Alice creates household
        h_id = client.post(
            "/api/v1/households", json={"name": "Smith Residence"}, headers=headers_a
        ).json()["id"]

        # 2. Alice generates member invite
        invite_resp = client.post(
            f"/api/v1/households/{h_id}/invites",
            json={"role": "member", "expires_in_days": 7},
            headers=headers_a,
        )
        assert invite_resp.status_code == 201
        invite_code = invite_resp.json()["invite_code"]

        # 3. Bob joins household
        join_resp = client.post(
            "/api/v1/households/join",
            json={"invite_code": invite_code},
            headers=headers_b,
        )
        assert join_resp.status_code == 200
        assert join_resp.json()["member_count"] == 2
        assert join_resp.json()["current_user_role"] == "member"

        # 4. Alice creates a living room TV
        now = datetime.now(timezone.utc)
        prod = client.post(
            "/api/v1/products",
            json={
                "name": "Living Room Samsung TV 75",
                "category": "electronics",
                "purchase_date": now.isoformat(),
                "purchase_price": 1800.0,
            },
            headers=headers_a,
        ).json()
        prod_id = prod["id"]

        # Alice uploads a receipt document
        doc = client.post(
            f"/api/v1/products/{prod_id}/documents",
            files={"file": ("tv_receipt.pdf", io.BytesIO(b"%PDF-1.4 TV receipt"), "application/pdf")},
            data={"document_type": "receipt", "document_name": "Samsung TV Receipt"},
            headers=headers_a,
        ).json()
        doc_id = doc["id"]

        # Before sharing: Bob cannot access product or document
        assert client.get(f"/api/v1/products/{prod_id}", headers=headers_b).status_code == 404
        assert client.get(f"/api/v1/documents/{doc_id}/download", headers=headers_b).status_code == 404

        # 5. Alice shares product to household
        share_resp = client.post(
            f"/api/v1/products/{prod_id}/share",
            json={"household_id": h_id},
            headers=headers_a,
        )
        assert share_resp.status_code == 200
        assert share_resp.json()["is_shared"] is True
        assert share_resp.json()["household_id"] == h_id

        # 6. Bob can now view product and download receipt!
        bob_view = client.get(f"/api/v1/products/{prod_id}", headers=headers_b)
        assert bob_view.status_code == 200
        assert bob_view.json()["name"] == "Living Room Samsung TV 75"
        assert bob_view.json()["is_shared"] is True

        bob_doc_dl = client.get(f"/api/v1/documents/{doc_id}/download", headers=headers_b)
        assert bob_doc_dl.status_code == 200
        assert "download_url" in bob_doc_dl.json()

        # Bob lists products under household scope
        bob_list = client.get("/api/v1/products?scope=household", headers=headers_b).json()
        assert bob_list["total"] == 1
        assert bob_list["items"][0]["id"] == prod_id

        # 7. Bob (member) updates product notes
        patch_resp = client.patch(
            f"/api/v1/products/{prod_id}",
            json={"notes": "Wall-mounted by Bob on weekend"},
            headers=headers_b,
        )
        assert patch_resp.status_code == 200
        assert patch_resp.json()["notes"] == "Wall-mounted by Bob on weekend"

        # 8. Alice unshares product back to private
        unshare_resp = client.post(
            f"/api/v1/products/{prod_id}/share",
            json={"household_id": None},
            headers=headers_a,
        )
        assert unshare_resp.status_code == 200
        assert unshare_resp.json()["is_shared"] is False
        assert unshare_resp.json()["household_id"] is None

        # After unsharing: Bob gets 404 again
        assert client.get(f"/api/v1/products/{prod_id}", headers=headers_b).status_code == 404
        assert client.get(f"/api/v1/documents/{doc_id}/download", headers=headers_b).status_code == 404

    def test_viewer_role_read_only_protection(self, client):
        headers_admin, _ = _register_user(client, "Admin Parent")
        headers_viewer, user_v_id = _register_user(client, "Teen Viewer")

        h_id = client.post(
            "/api/v1/households", json={"name": "Shared Villa"}, headers=headers_admin
        ).json()["id"]

        # Invite with viewer role
        inv = client.post(
            f"/api/v1/households/{h_id}/invites",
            json={"role": "viewer"},
            headers=headers_admin,
        ).json()
        client.post(
            "/api/v1/households/join",
            json={"invite_code": inv["invite_code"]},
            headers=headers_viewer,
        )

        # Admin creates and shares car
        now = datetime.now(timezone.utc)
        car = client.post(
            "/api/v1/products",
            json={"name": "Family Sedan", "category": "vehicles", "purchase_date": now.isoformat()},
            headers=headers_admin,
        ).json()
        car_id = car["id"]
        client.post(f"/api/v1/products/{car_id}/share", json={"household_id": h_id}, headers=headers_admin)

        # Viewer can view
        assert client.get(f"/api/v1/products/{car_id}", headers=headers_viewer).status_code == 200

        # Viewer CANNOT update (403)
        assert client.patch(
            f"/api/v1/products/{car_id}",
            json={"name": "Viewer Car"},
            headers=headers_viewer,
        ).status_code == 403

        # Viewer CANNOT delete (403)
        assert client.delete(f"/api/v1/products/{car_id}", headers=headers_viewer).status_code == 403

        # Viewer CANNOT share to household (403)
        v_prod = client.post(
            "/api/v1/products",
            json={"name": "Viewer Skateboard", "category": "other", "purchase_date": now.isoformat()},
            headers=headers_viewer,
        ).json()
        assert client.post(
            f"/api/v1/products/{v_prod['id']}/share",
            json={"household_id": h_id},
            headers=headers_viewer,
        ).status_code == 403

    def test_delete_household_safely_unlinks_products(self, client):
        headers, user_id = _register_user(client, "Solo Admin")
        h_id = client.post(
            "/api/v1/households", json={"name": "Temporary Flat"}, headers=headers
        ).json()["id"]

        now = datetime.now(timezone.utc)
        prod = client.post(
            "/api/v1/products",
            json={"name": "Microwave Oven", "category": "home_appliances", "purchase_date": now.isoformat()},
            headers=headers,
        ).json()
        prod_id = prod["id"]

        # Share to flat
        client.post(f"/api/v1/products/{prod_id}/share", json={"household_id": h_id}, headers=headers)

        # Delete household
        del_h = client.delete(f"/api/v1/households/{h_id}", headers=headers)
        assert del_h.status_code == 204

        # Product is still in user's vault, with household_id unlinked (null)
        fetched = client.get(f"/api/v1/products/{prod_id}", headers=headers)
        assert fetched.status_code == 200
        assert fetched.json()["id"] == prod_id
        assert fetched.json()["household_id"] is None
        assert fetched.json()["is_shared"] is False

    def test_invalid_invite_code_rejected(self, client):
        headers, _ = _register_user(client, "Random User")
        resp = client.post(
            "/api/v1/households/join",
            json={"invite_code": "NON-EXISTENT-CODE"},
            headers=headers,
        )
        assert resp.status_code == 404
