# City boundaries and POI assignment

This document describes how **municipality boundaries** are sourced, imported, and used to assign geospatial records to a **city**. The pipeline is **implemented** in this repository.

## Architecture decisions (fixed)

| Decision | Choice |
|----------|--------|
| **Boundary data source** | **[Geofabrik Greece OpenStreetMap extract](https://download.geofabrik.de/europe/greece.html)** — `greece-latest.osm.pbf` |
| **Extraction tool** | **[osmium-tool](https://osmcode.org/osmium-tool/)** (`tags-filter` + `export`) — **not** Osmosis, **not** osm2pgsql as the primary path |
| **City lookup method** | **PostGIS point-in-polygon** — `ST_Contains(city.boundary, point)` with optional **nearest-municipality buffer** for coastal points (`CITY_LOOKUP_BUFFER_METERS`, default 1500 m) |
| **Geohash** | **Not used** — no geohash columns, prefix tables, or geohash-based bucketing |

Geofabrik provides real administrative multipolygons suitable for `ST_Contains`. Geohash encodes coordinates into rectangular cells; it does **not** represent municipal borders and must **not** be used for city assignment.

## What “city” means

A **city** in PerTouriSM is a Greek **municipality (δήμος)**:

- OSM tag `boundary=administrative`
- OSM tag `admin_level=7` (default in the import script; adjustable with `--admin-level`)
- Named polygon (`name` or `name:el`)

We import **all** Greek municipalities (~332 rows after filtering) so Pelion δήμοι are available. Map defaults and seed data center on the **Pelion (Πήλιο)** pilot — mountain villages around Portaria, Makrinitsa, Zagora, and South Pelion.

Do **not** use:

- `place=city` / Geofabrik `places_a` shapefile polygons
- Regional/prefecture levels (`admin_level` 5–6) as the app “city”
- Geohash or reverse geocoding as the primary assignment method

## Current implementation overview

```mermaid
flowchart LR
  geofabrik["Geofabrik greece-latest.osm.pbf"]
  osmium_filter["osmium tags-filter"]
  osmium_export["osmium export GeoJSON"]
  import_script["scripts/import_cities.py"]
  cities[("cities table")]
  api["Site APIs"]
  chat["Chat API resolve_city_name"]
  geofabrik --> osmium_filter --> osmium_export --> import_script --> cities
  cities --> api
  cities --> chat
  api --> lookup["ST_Contains (+ buffer) → city_id"]
```

| Area | Implementation |
|------|----------------|
| **Database** | `cities` table + nullable `city_id` FK on `sites` (migration `b7e2f4a91c03`) |
| **Import** | `scripts/import_cities.py` + `make cities.import` |
| **Lookup** | `rest/app/services/cities.py` — `resolve_city_id()`, `resolve_city_name()`, `require_city_id()` |
| **Write path** | `sites.py` calls `require_city_id()` on create/update → **422** if outside all municipalities |
| **Read path** | List/detail responses include `city: CitySummary \| null` (`id`, `code`, `name_el`, `name_en`) |
| **Admin UI** | Site tables show municipality under coordinates via `LocationCell` |
| **Chat** | `chat_api.py` calls `resolve_city_name()` for the visitor’s coordinates |
| **Backfill** | Import script updates `city_id` on existing rows (containment + coastal buffer) |

Processed files live under `data/cities/` (large `.pbf` / `.geojson` are gitignored; provenance in `data/cities/SOURCE.txt`).

## Import pipeline (automated)

### Prerequisites

```bash
brew install osmium-tool   # macOS
# apt install osmium-tool  # Debian/Ubuntu

make infra.up
make migrate
make cities.import
```

`make cities.import` runs migrations, then `scripts/import_cities.py`.

### Steps performed by the script

1. **Download** `greece-latest.osm.pbf` from Geofabrik (or reuse with `--skip-download`).
2. **Filter** administrative relations:
   ```bash
   osmium tags-filter greece-latest.osm.pbf r/boundary=administrative \
     -o greece-admin-boundaries.osm.pbf --overwrite
   ```
3. **Export** to GeoJSON with relation IDs:
   ```bash
   osmium export greece-admin-boundaries.osm.pbf \
     -o greece-admin-boundaries.geojson --overwrite \
     --geometry-types=polygon,multipolygon \
     --add-unique-id=type_id
   ```
4. **Filter features** in Python:
   - `admin_level` matches (default `7`)
   - `boundary=administrative`
   - valid polygon geometry
   - OSM relation id present (from feature `id`, e.g. `a4693303`)
   - has a name (`name` or `name:el`)
5. **Upsert** into `cities` on `osm_id` conflict.
6. **Backfill** `city_id` on site rows (containment + coastal buffer; skip with `--skip-backfill`).

### Municipality codes

- Well-known overrides in `NAME_CODE_OVERRIDES` (e.g. Volos → `GR-VOL`, Zagora-Mouresi → `GR-ZAG`, South Pelion → `GR-SPI`).
- Other municipalities: `GR-{SLUG}-{osm_id}` (max 32 chars, unique per `osm_id`).

### CLI flags

| Flag | Purpose |
|------|---------|
| `--skip-download` | Reuse existing `greece-latest.osm.pbf` |
| `--skip-backfill` | Import boundaries only; do not update `city_id` on existing POIs |
| `--admin-level N` | OSM admin level (default `7`; inspect GeoJSON counts if import finds zero rows) |
| `--data-dir PATH` | Override `data/cities` (or `CITIES_DATA_DIR`) |

Direct invocation:

```bash
DATABASE_URL=postgresql+asyncpg://pertourism:password@localhost:5432/pertourism \
  python scripts/import_cities.py --skip-download
```

### Expected result

After a successful import:

- ~**332** municipalities in `cities`
- Pelion-area rows: `GR-VOL` / `GR-ZAG` / `GR-SPI` (if present in OSM extract)
- Existing POIs inside polygons get `city_id` backfilled

## Database schema

Defined in migration `rest/alembic/versions/b7e2f4a91c03_add_cities_and_city_id.py`:

```sql
-- cities
id          UUID PRIMARY KEY
osm_id      BIGINT NOT NULL UNIQUE
admin_level VARCHAR(8) NOT NULL
code        VARCHAR(32) NOT NULL UNIQUE
name_el     VARCHAR(255) NOT NULL
name_en     VARCHAR(255)
boundary    geometry(MULTIPOLYGON, 4326) NOT NULL
source      VARCHAR(64) NOT NULL DEFAULT 'geofabrik'
source_date DATE NOT NULL
created_at  TIMESTAMPTZ NOT NULL DEFAULT now()

CREATE INDEX ix_cities_boundary ON cities USING GIST (boundary);
```

`city_id` on domain tables:

- `sites.city_id` → `cities.id` (`ON DELETE SET NULL`)
- `noise_samples.city_id` → `cities.id`
- `gema_responses.city_id` → `cities.id`

`city_id` is **nullable** so legacy or coastal points outside polygons can exist; **new** creates/updates with a location must resolve a municipality or the API returns **422**.

## Runtime assignment (API)

### List filters

Sites, noise, and GEMA list endpoints accept optional query parameters:

| Parameter | Example | Description |
|-----------|---------|-------------|
| `city` | `?city=GR-ATH` | Exact municipality code, or partial match on Greek/English name |
| `city_id` | `?city_id=<uuid>` | Filter by city UUID |

Provide only one of `city` or `city_id`. Unknown or ambiguous `city` values return `404` or `400`.

### Cities catalog

`GET /cities` returns all imported municipalities as `CitySummary` rows (`id`, `code`, `name_el`, `name_en`), ordered by Greek name. Requires admin session.

### Map boundaries

`GET /maps/boundaries` returns a GeoJSON `FeatureCollection` of municipality polygons (admin session required). Optional filters:

| Parameter | Description |
|-----------|-------------|
| `city` | Single municipality by code or name |
| `city_id` | Single municipality by UUID |
| *(none)* | All imported municipalities |

The admin map can overlay all boundaries or a selected municipality from the catalog.

### Lookup

Municipality resolution uses strict containment first. When no polygon contains the point and `CITY_LOOKUP_BUFFER_METERS` is greater than zero (default **1500**), the nearest municipality whose boundary is within that distance (geography, metres) is assigned. Set `CITY_LOOKUP_BUFFER_METERS=0` to disable the buffer and require strict `ST_Contains`.

```python
# rest/app/services/cities.py
point = ST_SetSRID(ST_MakePoint(longitude, latitude), 4326)
# 1. ST_Contains(boundary, point)
# 2. else ST_DWithin(boundary::geography, point::geography, CITY_LOOKUP_BUFFER_METERS)
# ORDER BY contained first, then ST_Distance, then name_el
```

- `resolve_city_id()` → `UUID | None`
- `resolve_city_name()` → Greek municipality name or `None`
- `require_city_id()` → raises **422** when no municipality matches (inside polygon or within buffer)

### Create / update

On `POST` / `PATCH` with a location in:

- `rest/app/services/sites.py`
- `rest/app/services/noise.py`
- `rest/app/services/gema.py`

the service sets `city_id` from `require_city_id()`. There is **no** geohash fallback and **no** reverse-geocoding fallback.

### API responses

`CitySummary` in `rest/app/schemas/city.py`:

```json
{
  "id": "uuid",
  "code": "GR-VOL",
  "name_el": "Δήμος Βόλου",
  "name_en": "Volos Municipality"
}
```

Included on site list/detail payloads as optional `city`.

## Known limitations

| Topic | Behavior |
|-------|----------|
| **Coastal / offshore points** | Points outside all polygons but within `CITY_LOOKUP_BUFFER_METERS` (default 1500 m) of a municipality boundary are assigned to the **nearest** municipality. Points beyond the buffer keep `city_id = NULL` on backfill and fail on new create/update (**422**). Set buffer to `0` for strict containment only. |
| **Overlapping polygons** | If multiple municipalities match (contained or within buffer), contained matches win; then nearest boundary distance; then lexicographically first `name_el`. |
| **Unnamed OSM fragments** | Coastline/island features tagged `admin_level=7` without names are skipped at import. |
| **Refresh** | Re-run `make cities.import` to pick up Geofabrik updates; upserts by `osm_id`. |

## Explicitly out of scope

| Approach | Status |
|----------|--------|
| Geohash encode/decode or prefix → city maps | Rejected |
| Geofabrik GPKG/SHP `places_a` as boundary source | Not authoritative for δήμος |
| Bounding box only as city definition | Use full polygon |
| Reverse geocoding (Nominatim, Google, …) as primary source | Use PostGIS + Geofabrik |
| Osmosis | Not used; use osmium-tool |
| osm2pgsql / imposm as primary import | Not implemented; script uses osmium export + GeoJSON load |

Overpass may be used locally to preview a relation before running the national import; it is not the production data path.

## Operations

### Initial setup

```bash
make infra.up
make migrate
make cities.import
```

### Refresh boundaries (e.g. quarterly)

```bash
make cities.import
# or: python scripts/import_cities.py   # re-downloads PBF by default
```

Check `data/cities/SOURCE.txt` for last download metadata.

### Verify assignment

```sql
SELECT COUNT(*) FROM cities;

SELECT
  'sites' AS layer, COUNT(*) AS total, COUNT(city_id) AS matched
FROM sites
UNION ALL
SELECT 'noise', COUNT(*), COUNT(city_id) FROM noise_samples
UNION ALL
SELECT 'gema', COUNT(*), COUNT(city_id) FROM gema_responses;
```

## Licensing and attribution

| Source | License |
|--------|---------|
| Geofabrik / OpenStreetMap Greece extract | [ODbL 1.0](https://www.openstreetmap.org/copyright) |

Attribute OpenStreetMap if boundary derivatives are published. Comply with share-alike requirements for derived databases.

## Related documentation

- [`README.md`](../README.md) — `make cities.import`, map overview
- [`Description.md`](Description.md) — product vision (Pelion pilot)
- [`NativeBackendSetup.md`](NativeBackendSetup.md) — PostGIS setup
- [`MobileAPI.md`](MobileAPI.md) — mobile endpoints (chat includes `city_name`)

## References

- [Geofabrik — Greece](https://download.geofabrik.de/europe/greece.html)
- [PostGIS ST_Contains](https://postgis.net/docs/ST_Contains.html)
- [Osmium tags-filter](https://docs.osmcode.org/osmium/latest/osmium-tags-filter.html)
- [Osmium export](https://docs.osmcode.org/osmium/latest/osmium-export.html)
- [OpenStreetMap copyright / ODbL](https://www.openstreetmap.org/copyright)
