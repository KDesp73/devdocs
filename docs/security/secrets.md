# Secrets management

PerTouriSM never commits secrets. Local development uses a gitignored `.env` copied from `.env.example`.

## Environment variables (application)

| Variable | Purpose |
|----------|---------|
| `SECRET_KEY` | Admin session material + fallback for JWT/PII derivation |
| `JWT_SECRET` | HS256 signing key for mobile access tokens (defaults to `SECRET_KEY`) |
| `PII_ENCRYPTION_KEY` | Fernet key or passphrase for email/name at rest |
| `PII_BLIND_INDEX_KEY` | HMAC key for email lookup index |
| `ADMIN_PASSWORD` | Bootstrapped staff account password |
| `GARAGE_ACCESS_KEY` / `GARAGE_SECRET_KEY` | Object storage credentials |
| `OPENAI_API_KEY` | LLM provider |
| `GOOGLE_OAUTH_CLIENT_IDS` | Comma-separated Google OAuth client IDs |
| `APPLE_CLIENT_ID` | Apple Sign In audience (Services ID / bundle id) |
| `DATABASE_URL` | Postgres connection string |
| `SESSION_COOKIE_SECURE` | Set `true` behind HTTPS |

## Production mapping (AWS)

Inject the same names from **AWS Systems Manager Parameter Store** (SecureString) or **Secrets Manager** at deploy time (ECS task definition / Elastic Beanstalk / Kubernetes external-secrets). Example Parameter Store paths:

```
/pertourism/prod/SECRET_KEY
/pertourism/prod/JWT_SECRET
/pertourism/prod/PII_ENCRYPTION_KEY
/pertourism/prod/PII_BLIND_INDEX_KEY
/pertourism/prod/DATABASE_URL
/pertourism/prod/OPENAI_API_KEY
/pertourism/prod/GARAGE_SECRET_KEY
/pertourism/prod/GOOGLE_OAUTH_CLIENT_IDS
/pertourism/prod/APPLE_CLIENT_ID
```

Do not bake secrets into Docker images or this repository.

## TLS

Terminate TLS at the reverse proxy / load balancer for the pilot and production. Local docker-compose may use HTTP; set `SESSION_COOKIE_SECURE=true` when serving over HTTPS.

## Database encryption at rest

Prefer managed Postgres with storage encryption (e.g. RDS encryption) plus the application-level Fernet field encryption for visitor PII.
