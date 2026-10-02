# Pelion ingestion QA report

**Date:** 2026-09-29  
**Command:** `make etl.qa` after `make etl.osm` / `make etl.cams` / `make etl.elstat`

## Results (local / mock CAMS + Overpass fallback)

| Check | Result |
|-------|--------|
| OSM POIs (`source=osm`) | 5 (mock fallback after Overpass 406) |
| Curated/other sites | 101 |
| OSM settlements | 5 |
| CAMS indicators | 10 (mock — no `CAMS_API_KEY`) |
| ELSTAT rows | 3 (fixture CSV) |
| Unnamed OSM POIs | 0 |
| Empty categories | 0 |
| Anchors within 3 km | all villages ≥1 |

## Checklist

- [x] OSM POI count &gt; 0 (or mock fallback documented)
- [x] Unnamed OSM POIs reviewed / acceptable
- [x] Empty category count = 0
- [x] Village anchors have nearby POIs (3 km)
- [x] CAMS rows present when ADS configured (or mock noted)
- [x] ELSTAT fixture loaded (`ref_elstat_stats`)

## Notes / gaps

- Live Overpass returned HTTP 406 in this environment; pipeline fell back to mock Pelion anchors (`PIPELINES_ALLOW_MOCK=true`). Re-run with a valid `OSM_USER_AGENT` / alternate Overpass endpoint for production counts.
- Land cover (CLC) not in v1 automation; track as ΑΠΘ follow-up.
- Set `CAMS_API_KEY` for live ADS air-quality samples.
