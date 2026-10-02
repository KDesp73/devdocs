# References

## Platform libraries

- [pgvector](https://github.com/pgvector/pgvector)
- [PostGIS](https://postgis.net/)
- [MapLibre GL JS](https://maplibre.org/maplibre-gl-js/docs/)
- [Garage](https://garagehq.deuxfleurs.fr)

## Municipal boundaries (city assignment)

Municipality polygons for POI `city_id` assignment are imported from OpenStreetMap data via Geofabrik:

- [Greece OpenStreetMap data (Geofabrik)](https://download.geofabrik.de/europe/greece.html) — `greece-latest.osm.pbf` extract
- [Osmium Tool](https://osmcode.org/osmium-tool/manual) — `tags-filter` and `export` used by `scripts/import_cities.py`
- [OpenStreetMap copyright / ODbL 1.0](https://www.openstreetmap.org/copyright)

**Attribution:** © [OpenStreetMap](https://www.openstreetmap.org/copyright) contributors. Boundary derivatives are published under the [Open Database License (ODbL) 1.0](https://opendatacommons.org/licenses/odbl/). If you publish boundary GeoJSON or other derived databases, comply with ODbL share-alike requirements and retain OpenStreetMap attribution.

See [`CityBoundaries.md`](CityBoundaries.md) for the import pipeline and runtime lookup details.

## Pelion ETL (OSM POIs / CAMS / ELSTAT)

- [docs/ingestion/README.md](ingestion/README.md) — cron + Procrastinate + Bonobo pipelines
- [Copernicus Atmosphere Data Store (CAMS)](https://ads.atmosphere.copernicus.eu/) — air-quality forecasts (`CAMS_API_KEY`)
- [Overpass API](https://wiki.openstreetmap.org/wiki/Overpass_API) — Pelion POIs, paths, settlements
- [Hellenic Statistical Authority (ELSTAT)](https://www.statistics.gr/en/home) — reference population/tourism CSVs under `data/elstat/`
