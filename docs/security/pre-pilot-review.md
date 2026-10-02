# Pre-pilot security review

**Scope:** PerTouriSM backend (`rest/`), admin panel (`admin/`), auth/privacy features for the Pelion pilot.  
**Date:** 2026-09-25  
**Type:** Internal automated + checklist review (not a full external pen-test).

## Tools run

| Tool | Target | Result summary |
|------|--------|----------------|
| `pip-audit` | `requirements.txt`, `rest/requirements.txt` | **Local pass 2026-09-25:** no known vulnerabilities (0 High+) |
| `npm audit --audit-level=high` | `admin/package-lock.json` | **Local pass 2026-09-25:** 0 vulnerabilities |
| `bandit -r rest/app -ll` | Python SAST | **Local pass 2026-09-25:** 0 Medium+, 0 High; 1 Low (see F5) |
| Manual checklist | Auth, consent, export, erase, location minimization | See below |

CI continues to run the same commands on each PR (`backend.yml` / `admin.yml`).

## Manual checklist

- [x] Mobile access tokens are JWTs with short TTL; refresh tokens hashed and rotatable
- [x] Refresh reuse revokes token family
- [x] Guest accounts supported without email
- [x] Google/Apple id_token verification gated on configured client IDs
- [x] Exact visitor GPS not stored historically (zone geohash + city_id)
- [x] LLM prompts use municipality/zone, not exact coordinates
- [x] Consent purposes enforced on recommend / feedback / chat
- [x] `GET /app-users/me/export` returns subject JSON package
- [x] `DELETE /app-users/me` erases PII and anonymizes tour events
- [x] Rate limits on auth endpoints
- [x] Admin still uses HttpOnly session cookie
- [x] Admin back-office: view consents + export subject JSON + erase via app-user edit page

## Findings & remediations

| ID | Severity | Finding | Remediation | Status |
|----|----------|---------|-------------|--------|
| F1 | Medium | Historical exact GPS on tour events / chat | Migrated to zone geohash; dropped lat/lng columns | Fixed |
| F2 | Medium | Opaque long-lived Bearer sessions | Replaced with JWT + refresh | Fixed |
| F3 | Low | No dependency scanning in CI | Added pip-audit, npm audit, Dependabot | Fixed |
| F4 | Info | LLM still receives nearby site names (necessary for guide) | Documented as third-party processing under `chat_llm` consent | Accepted |
| F5 | Low | Bandit B110 `try/except/pass` in `rest/app/core/pii.py` Fernet key derivation fallback | Intentional: invalid base64 passphrase falls through to SHA-256 derivation; no silent security failure | Accepted |

## Residual risks

- Social login misconfiguration (wrong audience) returns 401/503 — operators must set client IDs before store builds.
- Application-level PII encryption key rotation is manual (re-encrypt job not yet automated).
- Admin cookie `Secure` defaults to false for local HTTP — must be true in HTTPS pilot deploy.
