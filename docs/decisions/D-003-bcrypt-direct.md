# D-003: Replace passlib with Direct bcrypt

**Status:** Accepted · **Date:** 2026-09-23 · **Phase:** 1

## Context

`app/core/security.py` used passlib's `CryptContext` for bcrypt hashing. On
this machine the installed combination (passlib 1.7.4 + bcrypt 5.0.0) fails at
runtime: passlib reads `bcrypt.__about__` (removed in bcrypt 4.1+) and its
legacy bug-detection path raises `ValueError: password cannot be longer than
72 bytes`. passlib is effectively unmaintained (no release since 2020).

## Decision

Remove passlib. Call `bcrypt` directly in `app/core/security.py`.

## Why

- Fixes a hard runtime failure with zero behavior change for callers.
- Removes an unmaintained dependency; one less supply-chain surface.
- bcrypt alone already embeds salt and cost in the output hash
  (`$2b$12$...`); passlib added indirection, not security.
- Cost is environment-tunable (`BCRYPT_ROUNDS`, default 12; tests use 4).

## Alternatives Considered

| Option | Verdict |
|---|---|
| Pin bcrypt==4.0.1 to please passlib | Rejected: freezes an old bcrypt forever to satisfy a dead library |
| argon2 via passlib/argon2-cffi | Rejected: reintroduces unmaintained passlib; bcrypt >= 12 rounds is accepted industry standard |
| Direct bcrypt (chosen) | Minimal, maintained, runtime-verified |

## Consequences

- `hash_password`/`verify_password` signatures unchanged; all call sites
  untouched.
- Passwords > 72 bytes are truncated (bcrypt's native limit) — consistent with
  common practice; max-length enforcement should be added at the schema level
  in a future hardening pass.
- passlib-produced hashes (if any user data existed) remain verifiable —
  `checkpw` reads the same `$2b$` format.
