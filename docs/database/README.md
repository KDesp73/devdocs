# Database documentation

PerTouriSM stores application data in **PostgreSQL 16** with **PostGIS** (SRID **4326**, GiST spatial indexes) and **pgvector** for semantic search.

## MongoDB / Elasticsearch (DoD instruction 3)

The pilot **does not** run MongoDB or Elasticsearch. Unstructured review text and full-text search use **Postgres FTS** (`tsvector` / GIN on `reviews.search_vector`). Semantic similarity for site descriptions uses **pgvector** embeddings on `sites.embedding`.

This is the approved substitute for the brief’s “MongoDB and/or ElasticSearch” item for the Pelion pilot.

## Documents in this folder

| File | Purpose |
|------|---------|
| [schema.md](schema.md) | Entity catalog and DoD name mapping |
| [er.md](er.md) | ER diagram for ΑΠΘ / PM review (pending formal approval) |
| [naming.md](naming.md) | Table/column naming conventions |
| [anonymization.md](anonymization.md) | Interaction pseudonyms and erase rules |

## Spatial DoD

- POIs: `sites.location` (`geometry(Point,4326)` + GiST)
- Routes: `routes.geometry` (`geometry(LineString,4326)` + GiST)
- Nearby API: `GET /sites/nearby?lat=&lng=&radiusMeters=5000` uses `ST_DWithin` on geography
- Bench: `make seed.pelion` then `make bench.spatial` (budget **&lt; 100 ms**)
