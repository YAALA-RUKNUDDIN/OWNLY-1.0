# D-013: Household & Family Sharing — RBAC, Product Vaults & Invite Codes

**Status:** Accepted · **Date:** 2026-09-24 · **Phase:** 8

## Context

OWNLY's initial architecture maintained strict single-user tenancy isolation where all products, warranties, reminders, and documents belonged strictly to `user_id`. In real-world households, families and roommates frequently co-own appliances, electronics, home systems, and vehicles, necessitating:
1. **Multi-User Vault Access:** The ability for household members to view shared appliances, manuals, and receipts without sharing individual account credentials.
2. **Privacy-Preserving Vault Scoping:** Maintaining personal vaults by default where items are strictly private unless explicitly shared to a household vault.
3. **Role-Based Access Control (RBAC):** Distinct permissions between household `admin`, `member`, and `viewer` roles to protect warranties and ownership records against unauthorized modification or deletion.
4. **Frictionless Onboarding:** Secure, time-bound invite codes (`OWN-XXXX-XXXX`) allowing new members to join a household with one tap.
5. **Safe Cascade Deletion:** Guaranteeing that deleting a household never destroys personal ownership records or attached documents; shared products automatically revert to their owner's personal vault.

## Decision

- **Data Model & Invariants (`app/models/household.py` & `app/models/product.py`):**
  - Added `HouseholdRole` enum (`admin`, `member`, `viewer`).
  - Added `Household` table with unique UUID, name, creator ID, and timestamps.
  - Added `HouseholdMember` join table with `(household_id, user_id)` primary key, role, and join timestamp.
  - Added `HouseholdInvite` table with unique 12-character uppercase invite code (`OWN-XXXX-XXXX`), role, and configurable expiration.
  - Modified `Product` table: added nullable `household_id` foreign key referencing `households.id` with `ondelete="SET NULL"` and index.
  - Invariant: A product is personal when `household_id IS NULL`. When `household_id` is set, members of that household gain access according to their role.

- **RBAC & Authorization Matrix (`app/repositories/product_repo.py` & `app/services/household_service.py`):**
  - **Owner (`product.user_id == caller.id`):** Full control over the product at all times (can edit, delete, unlink from household, or delete documents).
  - **Admin (`HouseholdRole.admin`):** Full administrative rights over the household (rename, delete household, create invites, remove members) and shared products.
  - **Member (`HouseholdRole.member`):** Can view shared products, edit metadata, upload receipts/manuals, and manage timeline events.
  - **Viewer (`HouseholdRole.viewer`):** Strict read-only access. Can view products, download documents, and view warranties/repairs, but receives `403 Forbidden` on PATCH, DELETE, or share operations.

- **Query Scoping & Isolation:**
  - `ProductRepository.get()` and query filters evaluate `(user_id == caller.id) OR (household_id.in_(caller_household_ids))`.
  - Added `scope` parameter (`all`, `personal`, `household`) enabling users to filter their vaults.
  - Document downloads (`DocumentRepository.get_for_user()`) verify caller is either the document owner or an active member of the product's shared household.

- **Invite Flow & Safe Cascades:**
  - Secure random invite codes formatted as `OWN-XXXX-XXXX` with expiration timestamps (default 7 days).
  - Single-use invite redemption prevents replay attacks.
  - Deleting a household executes `UPDATE products SET household_id = NULL WHERE household_id = :id`, preserving all products, receipts, warranties, and timeline entries in their owners' vaults.

- **Mobile Implementation (Flutter & Riverpod):**
  - Models: `HouseholdItem`, `HouseholdMemberItem`, `HouseholdDetailItem`, and `HouseholdInviteItem`.
  - Repository: `HouseholdRepository` with `listHouseholds()`, `getHousehold()`, `createHousehold()`, `createInvite()`, `joinHousehold()`, `removeMember()`, and `shareProduct()`.
  - UI Screen: `HouseholdScreen` supporting household switching, role badges, member management, invite code modal with clipboard copying, and join code entry.
  - Routing: Registered `/households` route with `ownly:///households` deep-link support, accessible from Profile > Account.
  - Product Detail Integration: Vault share action in product detail AppBar and header badge indicating shared status.

## Consequences

- Full backward compatibility: existing single-user vaults operate identically with zero data migration friction.
- Shared vaults enable collaborative household inventory management without compromising personal privacy.
- 132 backend tests and 24 mobile tests validate all operational paths with 100% green status.
