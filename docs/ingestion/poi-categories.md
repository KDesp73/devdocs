# POI category schema (ΑΠΘ contract)

Canonical slugs shared by mobile interests interests, `categories` / `site_categories`, and OSM ETL.

Source of truth in code: [`recommendations/taxonomy.py`](../../recommendations/taxonomy.py) and [`sources/osm/categories.py`](../../sources/osm/categories.py).

## Canonical slugs

| Slug | EL | EN |
|------|----|----|
| history | Ιστορία | History |
| architecture | Αρχιτεκτονική | Architecture |
| museum | Μουσείο | Museum |
| viewpoint | Θέα | Viewpoint |
| religious | Θρησκευτικά | Religious |
| culture | Πολιτισμός | Culture |
| food | Γαστρονομία | Food |
| family | Οικογένεια | Family |
| nature | Φύση | Nature |
| accessibility | Προσβασιμότητα | Accessibility |

## OSM tag → slug map

| OSM tags | Slug |
|----------|------|
| `tourism=museum` | museum |
| `tourism=viewpoint` | viewpoint |
| `tourism=attraction\|gallery\|artwork` | culture |
| `historic=*` (castle, ruins, monument, …) | history |
| `amenity=place_of_worship` | religious |
| `amenity=restaurant\|cafe` | food |
| `amenity=theatre\|arts_centre` | culture |
| `natural=peak\|beach\|wood\|spring` | nature |
| `leisure=park` | nature |
| `leisure=playground` | family |

Multi-tag features keep **all** matched slugs (deduped). Unknown tags are ignored; if nothing matches, ETL assigns `culture`.

## Sign-off

This document is the proposed unified schema for ΑΠΘ / Π2.4. Formal written approval is external to the repo.
