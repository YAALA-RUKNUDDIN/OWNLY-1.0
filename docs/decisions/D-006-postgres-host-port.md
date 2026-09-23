# D-006: Docker PostgreSQL on Host Port 5433 (Native-Postgres Clash)

**Status:** Accepted · **Date:** 2026-09-23 · **Phase:** 1 (verification)

## Context

PostgreSQL-parity verification required the Dockerized Postgres 16 from
`backend/docker-compose.yml` to be reachable from the host. On this machine the
container failed to accept connections even though Docker reported it healthy:

- A **native Windows PostgreSQL service** was already listening on `0.0.0.0:5432`.
- The Docker port mapping `5432:5432` therefore collided with the native
  service. Host requests to `localhost:5432` were answered by the *native*
  server, so the `ownly` role/password did not exist and authentication failed
  (`FATAL: password authentication failed for user "ownly"`).
- An earlier stale Docker volume (created with different credentials) produced a
  second, unrelated failure mode and was removed.

## Decision

Publish the Docker Postgres container on **host port 5433** (`"5433:5432"`) and
treat 5433 as the local host port for the Dockerized database everywhere the
host connects to it:

| Location | Value |
|---|---|
| `backend/docker-compose.yml` | `"5433:5432"` |
| `backend/.env.example` | `...@localhost:5433/ownly` (documented) |
| `backend/app/core/config.py` default | `...@localhost:5433/ownly` |
| `backend/tests/conftest.py` default test DB | `...@localhost:5433/ownly_test` |
| `backend/_check_import.py` docstring | 5433 |

Inside the Docker network nothing changes: the backend container still reaches
Postgres at `postgres:5432` (see `README.md`).

## Why

- Remove the class of bug where "the tests connected to the wrong server and
  failed with an auth error that looks like a code bug". This actually happened
  once during verification (`conftest` fallback pointed at 5432 → native server
  → 63 errors).
- Do not disturb a machine-level service the user may depend on; the port remap
  is local-config only and invisible to production, where Postgres is addressed
  by service name on its native port.

## Alternatives Considered

| Option | Verdict |
|---|---|
| Stop/uninstall the native Windows PostgreSQL service | Rejected: destructive to the user's machine, outside project scope, not reproducible for other devs |
| Change the native service's port | Rejected: same destructiveness, and the OS-level config is not part of the repo |
| Ask the user to pick a port case-by-case each session | Rejected: repeated friction; a single documented convention is better |
| Publish on 5433 (chosen) | Local-only, zero impact on the native service or on production topology |

## Consequences

- Any doc or script that connects **from the host** must use 5433.
- Anyone with a free 5432 can still run `"5432:5432"`; the port is a compose
  detail, not an application contract. Application code only reads `DATABASE_URL`.
- `docker-compose.yml`'s obsolete `version:` key was dropped at the same time
  (Compose v2 warns on it).
- Verification is now stable and repeatable:
  `TEST_DATABASE_URL=postgresql+psycopg2://ownly:ownly_secret@localhost:5433/ownly_test`
  → full suite green on real Postgres (see README verification status).

## Evidence

- Two PostgreSQL-only failures were found and fixed thanks to this parity run
  (a naive/aware datetime comparison in `PATCH /warranties/{id}`, and a
  baseline-migration `downgrade()` that left native ENUM types behind,
  breaking re-upgrade). Details in D-002 consequences.
- `alembic upgrade head → downgrade base → upgrade head` executed repeatedly
  against the Docker Postgres with no errors.
