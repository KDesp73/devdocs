# Schema catalog (DoD mapping)

| DoD entity | Physical table(s) | Notes |
|------------|-------------------|--------|
| users | `users`, `app_users` | Admin panel vs mobile visitors |
| preferences | `app_users.interest_tags`, profile flags, `app_user_consents` | No separate `preferences` table |
| pois | `sites` | POINT 4326 + GiST; embedding via pgvector; `source`/`source_id`/`imported_at` for ETL |
| categories | `categories`, `site_categories` | Normalized; legacy `categories` text[] kept in sync by seeds/ETL |
| routes | `routes` | LINESTRING 4326 + GiST; OSM path/track via ETL |
| settlements | `settlements` | OSM place=* villages/towns |
| events | `local_events` | Calendar / pilot events (not tour feedback) |
| reviews | `reviews` | Body text + generated `search_vector` (FTS) |
| media | `site_media` | Objects in Garage S3 |
| visits / interactions | `tour_recommendation_events`, `zone_visit_counters` | Zone geohash; `pseudonym_id` |
| environmental_indicators | `environmental_indicators` | POINT samples (type/value/unit/time); CAMS ETL provenance |
| ref_elstat_stats | `ref_elstat_stats` | ELSTAT population/tourism reference rows |

Supporting: `cities` (municipality MultiPolygon), `chat_sessions` / `chat_messages`, auth/session/refresh tables, Procrastinate `procrastinate_*` (job queue).

Migrations: Alembic under `rest/alembic/versions/` (never hand-edit production schema).
Ingestion: [`docs/ingestion/README.md`](../ingestion/README.md).
