# Native Backend Setup (Without Docker)

This guide installs and runs the PerTouriSM **backend services on the host machine** without Docker. It covers PostgreSQL (with PostGIS and pgvector) and the FastAPI API.

The admin panel (Next.js) is separate; see [README.md](../README.md) for admin setup. You can run the API alone for development and testing with `curl` or an HTTP client.

## What runs where

```mermaid
flowchart LR
  subgraph host [Host machine]
    API[FastAPI on :8000]
    PG[(PostgreSQL + PostGIS + pgvector)]
    API --> PG
  end
```

| Service | Required? | Default port | Purpose |
|---------|-----------|--------------|---------|
| PostgreSQL + PostGIS + pgvector | Yes | 5432 | Application data, geospatial types, embeddings |
| FastAPI (Uvicorn) | Yes | 8000 | REST API |

---

## Prerequisites

- **Python 3.11 or 3.12** (recommended; used by `scripts/sourceme`)
- **PostgreSQL 16** with **PostGIS 3.4+** and **pgvector**
- **Make** (optional; wraps common commands)
- **Git** and a clone of this repository

On macOS you will typically use Homebrew. On Linux, use your distribution’s PostgreSQL/PostGIS packages.

---

## 1. PostgreSQL, PostGIS, and pgvector

The backend expects the same extensions that Docker initializes in [`docker/db-init/01_init.sql`](../docker/db-init/01_init.sql):

```sql
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS vector;
```

### macOS (Homebrew)

```bash
brew install postgresql@16 postgis pgvector
brew services start postgresql@16
```

Add PostgreSQL to your `PATH` if needed (Homebrew prints instructions after install), for example:

```bash
export PATH="/opt/homebrew/opt/postgresql@16/bin:$PATH"
```

### Linux (Debian/Ubuntu example)

```bash
sudo apt update
sudo apt install postgresql-16 postgresql-16-postgis-3 postgresql-16-pgvector
sudo systemctl enable --now postgresql
```

Package names vary by distribution. You need PostgreSQL 16, PostGIS, and pgvector for the same major PostgreSQL version.

### Create database and role

Match the credentials you will put in `.env` (defaults shown):

```bash
psql postgres <<'SQL'
CREATE USER pertourism WITH PASSWORD 'change_me';
CREATE DATABASE pertourism OWNER pertourism;
GRANT ALL PRIVILEGES ON DATABASE pertourism TO pertourism;
SQL
```

Enable extensions (connect as a superuser or the DB owner):

```bash
psql -d pertourism <<'SQL'
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS vector;
SQL
```

Verify:

```bash
psql -d pertourism -c "SELECT PostGIS_Version();"
psql -d pertourism -c "SELECT extname FROM pg_extension WHERE extname IN ('postgis', 'vector');"
```

---

## 2. Python environment

From the repository root:

```bash
cp .env.example .env
# Edit .env — see section 4 below
```

Activate the shared virtual environment and install dependencies:

```bash
source scripts/sourceme
```

`sourceme` will:

- Create `.venv` at the repo root
- Install packages from [`requirements.txt`](../requirements.txt)
- Load `.env`
- Rewrite `DATABASE_URL` from `@postgres:` to `@localhost:` for host development
- Set `PYTHONPATH` for `rest`, `speech`, `chat`, and `recommendations`

Alternatively, without sourcing:

```bash
make backend.install
```

---

## 3. Environment configuration

Edit [`.env`](../.env.example) for native services. Important values:

```env
# Database — use localhost, not "postgres"
POSTGRES_USER=pertourism
POSTGRES_PASSWORD=change_me
POSTGRES_DB=pertourism
POSTGRES_PORT=5432

# Backend reads this; host URL must use localhost
DATABASE_URL=postgresql+asyncpg://pertourism:change_me@localhost:5432/pertourism

# API
BACKEND_PORT=8000
CORS_ORIGINS=http://localhost:3000

# Auth (admin user bootstrapped on API startup)
SECRET_KEY=change_me_to_a_long_random_string
ADMIN_EMAIL=admin@example.com
ADMIN_PASSWORD=change_me
ADMIN_FULL_NAME=Admin

# Speech routes (optional)
OPENAI_API_KEY=
```

Generate a secret key:

```bash
make keygen
```

---

## 4. Database migrations

Apply the Alembic schema (users, auth sessions, sites, cities, routes, reviews, etc.):

```bash
make db.check    # optional: verify Postgres credentials
make migrate
```

This runs `alembic upgrade head` against `localhost` using `POSTGRES_*` from `.env`.

Manual equivalent:

```bash
source scripts/sourceme
cd rest
alembic upgrade head
```

---

## 5. Run the API

### Using Make (recommended)

```bash
make backend.dev
```

This runs migrations first, then starts Uvicorn with hot reload on port `8000`.

### Manual start

```bash
source scripts/sourceme
cd rest
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

On startup the API bootstraps the admin user from `ADMIN_EMAIL` / `ADMIN_PASSWORD` in `.env`.

---

## 6. Verify the stack

| Check | Command / URL |
|-------|----------------|
| API health | `curl http://localhost:8000/health` |
| Admin login | `curl -c cookies.txt -X POST http://localhost:8000/auth/login -H 'Content-Type: application/json' -d '{"email":"admin@example.com","password":"change_me"}'` |
| Current user | `curl -b cookies.txt http://localhost:8000/auth/me` |

---

## 7. Startup order (quick reference)

```bash
# 1. Start PostgreSQL (OS service)
# macOS: brew services start postgresql@16
# Linux: sudo systemctl start postgresql

# 2. From repo root
cp .env.example .env          # first time only
source scripts/sourceme       # or: make backend.install
make migrate
make backend.dev
```

---

## 8. Troubleshooting

### `relation "users" does not exist`

Migrations were not applied. Run `make migrate` before starting the API.

### `password authentication failed for user "pertourism"`

The password in `.env` does not match the PostgreSQL role. Update the role password:

```bash
psql postgres -c "ALTER USER pertourism WITH PASSWORD 'your_password';"
```

### `make db.check` fails

- Confirm PostgreSQL is running: `pg_isready -h localhost -p 5432`
- Confirm `POSTGRES_PORT` in `.env` matches your server
- Confirm `DATABASE_URL` uses `localhost`, not `postgres`

### Speech endpoints fail

Set `OPENAI_API_KEY` in `.env`. The `faster-whisper` dependency is installed for STT; first run may download models.

### Python version errors from `sourceme`

Install Python 3.11 or 3.12. The script does not activate 3.14 by default.

---

## Related documentation

- [README.md](../README.md) — full project overview and hybrid Docker workflow
- [References.md](References.md) — external links (MapLibre, pgvector)
- [Description.md](Description.md) — product goals and domain context
