# Recommendation Service

Python FastAPI microservice for tour recommendations (DoD surface).  
**Location:** [`recommendations/service/`](../../recommendations/service/) (package `recsvc`).

## Endpoints

| Method | Path | Auth |
|--------|------|------|
| GET | `/recommendations` | Bearer + `recommendations` consent |
| POST | `/feedback` | Bearer + `analytics_zone` consent |
| GET | `/routes/suggested` | Bearer + `recommendations` consent |
| GET | `/health` | public |
| GET | `/docs` | OpenAPI |

Query context for recommend/suggested: `lat`, `lng`, `time`, `weather` (`clear|clouds|rain|hot|cold`), `travelMode` (`walk|bike|drive`), `maxSites`, `maxDurationMinutes`.

## Ports / compose

- Service: `http://localhost:8001` (`RECOMMENDATION_PORT`)
- Redis: `localhost:6379`
- Main REST proxies `/mobile/tours/recommend|feedback|suggested-route` → this service (`RECOMMENDATION_SERVICE_URL`)

## Cache

Key: `rec:v1:{user_id}:{geohash}:{hour}:{weather}:{mode}:{maxSites}:{maxDuration}`  
TTL: `CACHE_TTL_SECONDS` (default 90). Invalidated on feedback.

## Local run

```bash
# Host process (no recommendation container):
make infra.up          # postgres (+ optionally redis)
make rec.dev   # http://localhost:8001 — OpenAPI at /docs

# Or Docker:
make rec.up
```

## Tests / load / sim

```bash
make rec.test
REC_ACCESS_TOKEN=<jwt> make rec.load
make rec.sim
SIM_JSONL=data/simulations/….jsonl make rec.analyze
```
