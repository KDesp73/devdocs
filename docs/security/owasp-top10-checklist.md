# OWASP Top 10 checklist (PerTouriSM)

Mapped to controls in this codebase for the Pelion pilot. Review before each production release.

| ID | Risk | Control in PerTouriSM | Status |
|----|------|------------------------|--------|
| A01 | Broken Access Control | Admin cookie sessions; mobile JWT `sub` ownership checks on chat/tours; consent gates | Implemented |
| A02 | Cryptographic Failures | Argon2 passwords (`pwdlib`); JWT HS256; Fernet PII; hashed refresh tokens; TLS at edge | Implemented |
| A03 | Injection | SQLAlchemy bound parameters; Pydantic validation on all public bodies | Implemented |
| A04 | Insecure Design | Data minimization (zone geohash, no exact GPS history); consent purposes; guest mode | Implemented |
| A05 | Security Misconfiguration | Secrets via env/SSM; CORS allowlist; `SESSION_COOKIE_SECURE` for HTTPS; Garage keys not in git | Implemented |
| A06 | Vulnerable Components | CI `pip-audit`, `npm audit`, Dependabot | Implemented |
| A07 | Identification & Auth Failures | Short-lived JWT + rotating refresh; reuse detection; rate limits on auth endpoints; Google/Apple id_token verify | Implemented |
| A08 | Software & Data Integrity | Dependency scans; no unsigned webhooks in scope | Partial |
| A09 | Security Logging Failures | FastAPI/uvicorn access logs; expand structured audit log post-pilot | Partial |
| A10 | SSRF | Outbound LLM/Garage URLs from env only; no user-controlled fetch URLs | Implemented |

## Residual / follow-ups

- Add structured security audit log for consent changes and account erasure.
- Consider RS256 JWT with rotating keys for multi-instance production.
- External pen-test before full public launch (beyond automated pre-pilot review).
