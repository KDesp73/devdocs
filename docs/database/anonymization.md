# Interaction anonymization

Related: [P4.4 GDPR technical](../compliance/P4.4-gdpr-technical.md).

## Pseudonymous interactions

Tour recommendation events and reviews may carry:

| Column | Purpose |
|--------|---------|
| `app_user_id` | Live account link (nullable after erase) |
| `pseudonym_id` | Stable UUID for analytics continuity |

**Derivation:** `uuid5(NAMESPACE_URL, "pertourism:app-user:{app_user_id}")` — see `rest/app/core/pseudonym.py`. Deterministic, non-reversible to email/name without the original user id mapping.

On write (`record_tour_feedback`), `pseudonym_id` is set whenever an app user is known.

## Location minimization

Exact GPS is **not** stored on historical tour events. Events keep `city_id` + `zone_geohash` only.

## Erase (`DELETE /app-users/me` or admin delete)

1. Revoke refresh tokens  
2. Delete chat sessions/messages  
3. Null `app_user_id` (and session) on tour events — **keep** `pseudonym_id` and zone aggregates  
4. Null `app_user_id` on reviews — keep body/`pseudonym_id` for aggregate quality signals  
5. Delete consents and the `app_users` row  

Zone visit counters remain municipality/zone aggregates without personal identifiers.
