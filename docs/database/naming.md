# Naming conventions

- **Tables / columns:** `snake_case`, plural table names (`reviews`, `routes`).
- **Primary keys:** `id` as UUID (`gen` via app / `uuid4` / deterministic `uuid5` for seeds).
- **Foreign keys:** `{table_singular}_id` (e.g. `city_id`, `site_id`, `app_user_id`).
- **Timestamps:** `created_at`, `updated_at`, `observed_at`, `starts_at` as `timestamptz` (`DateTime(timezone=True)`).
- **Booleans:** affirmative adjectives (`is_guest`, `wheelchair_accessible`).
- **Geometry columns:**
  - Points: prefer `location`
  - Lines: prefer `geometry` on `routes`
  - Polygons: `boundary` on `cities`
  - Always **SRID 4326**; GiST indexes named `ix_{table}_{column}`
- **API JSON:** camelCase aliases via Pydantic `serialization_alias` / `alias`.
- **Slugs:** lowercase ASCII for `categories.slug`.
- **Indexes:** `ix_{table}_{column}`; unique constraints `uq_{table}_{cols}`.
