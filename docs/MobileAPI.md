# Mobile app API

The mobile client uses **OAuth2-style Bearer JWT authentication**.

- **Access token:** short-lived JWT in `Authorization: Bearer <accessToken>`
- **Refresh token:** long-lived opaque token; rotate via `POST /app-users/token/refresh`
- Issue tokens with register, login, guest, or Google/Apple Sign-In
- Revoke with `POST /app-users/logout` (send `refreshToken` in body)

Interactive API docs: `http://localhost:8000/docs` (tags **app-users**, **mobile**).  
Recommendation microservice OpenAPI: `http://localhost:8001/docs` (`GET /recommendations`, `POST /feedback`, `GET /routes/suggested`). Mobile `/mobile/tours/*` proxies to that service.

## Authentication

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `POST` | `/app-users` | — | Register (email+password); returns user + `accessToken` + `refreshToken` |
| `POST` | `/app-users/login` | — | Password login |
| `POST` | `/app-users/guest` | — | Anonymous guest account + tokens |
| `POST` | `/app-users/token/refresh` | — | Body `{ "refreshToken" }`; rotates refresh family |
| `POST` | `/app-users/oauth/google` | — | Body `{ "idToken", "guestAccessToken?" }` |
| `POST` | `/app-users/oauth/apple` | — | Body `{ "idToken", "guestAccessToken?" }` |
| `POST` | `/app-users/logout` | — | Body `{ "refreshToken?" }`; revokes refresh family |
| `GET` | `/app-users/me` | Bearer | Current profile |
| `PATCH` | `/app-users/me` | Bearer | Update profile / password |
| `GET` | `/app-users/me/consents` | Bearer | List consent purposes |
| `PUT` | `/app-users/me/consents` | Bearer | Update consents `{ "consents": { "recommendations": true, ... } }` |
| `GET` | `/app-users/me/export` | Bearer | GDPR export JSON package |
| `DELETE` | `/app-users/me` | Bearer | Erase account (PII delete + anonymize analytics) |

Register and update bodies use **snake_case**. Responses use **camelCase** (e.g. `firstName`, `accessToken`, `refreshToken`, `isGuest`).

```json
POST /app-users
{
  "email": "user@example.com",
  "first_name": "Alex",
  "last_name": "Visitor",
  "password": "password123",
  "interests": ["history", "architecture"],
  "age_group": "adult",
  "accessibility_needs": false,
  "has_children": false
}
```

### Required mobile consent UX

Present **separate screens or toggles** for each purpose before enabling the feature:

| Purpose | Gate |
|---------|------|
| `account` | Storing email / social identity |
| `recommendations` | Personalized tours (`POST /mobile/tours/recommend`) |
| `analytics_zone` | Tour feedback → zone aggregates (`POST /mobile/tours/feedback`) |
| `chat_llm` | AI chat (`POST /mobile/chat/ask`) |

Missing consent → `403` with `{ "code": "CONSENT_REQUIRED", "purpose": "..." }`.

### Social login

Configure `GOOGLE_OAUTH_CLIENT_IDS` and `APPLE_CLIENT_ID` on the backend. The app obtains an id_token from the provider SDK and posts it to `/app-users/oauth/google` or `/oauth/apple`. Optional `guestAccessToken` links a prior guest into the registered identity.

## Mobile routes (`/mobile/*`)

All routes below require `Authorization: Bearer <accessToken>`.

| Method | Path | Notes |
|--------|------|-------|
| `GET` | `/mobile/sites` | List POIs |
| `GET` | `/mobile/sites/{id}` | Detail |
| `GET` | `/mobile/sites/{id}/media/{mediaId}/file` | Stream media |
| `GET` | `/mobile/maps/config` | Default center/zoom/layers |
| `GET` | `/mobile/speech/metadata` | TTS voices / formats |
| `POST` | `/mobile/speech/tts` | Synthesize speech |
| `POST` | `/mobile/speech/stt` | Transcribe upload |
| `POST` | `/mobile/tours/recommend` | Proxied to Recommendation Service; requires `recommendations` consent; optional query `weather`, `travelMode`, `time`. Each stop includes `reasons[]` (1–3 bilingual explanations). |
| `POST` | `/mobile/tours/feedback` | Proxied; requires `analytics_zone`; stores **zone geohash + city**, not exact GPS |
| `GET` | `/mobile/tours/suggested-route` | Proxied `GET /routes/suggested`; LineString + ordered stops |
| `GET` | `/mobile/chat/sessions` | List sessions |
| `POST` | `/mobile/chat/sessions` | Create session |
| `GET` | `/mobile/chat/sessions/{sessionId}` | Detail (zone fields, not exact lat/lng) |
| `DELETE` | `/mobile/chat/sessions/{sessionId}` | Delete session |
| `POST` | `/mobile/chat/ask` | Requires `chat_llm` |

### Tour recommend — `reasons` (T4.2)

Each stop in `POST /mobile/tours/recommend` (and Recommendation Service `GET /recommendations`) may include:

```json
"reasons": [
  {
    "code": "interest",
    "feature": "interest",
    "text": {
      "el": "Ταιριάζει με το ενδιαφέρον σου για φύση / πεζοπορία",
      "en": "Matches your interest in nature / hiking"
    }
  }
]
```

- Always prefer rendering `text.el` or `text.en` based on the app locale (1–3 items).
- Reasons are derived from scorer feature contributions (interest, proximity, weather, PM2.5, time of day, settlement, CF/CB)—not generic marketing copy.
- Optional profile field `gender` (`female` | `male` | `other` | `prefer_not_to_say`) may be set on register/update; it is **not** used by the ranking algorithm.

### Tour feedback body

Still accepts `location: { latitude, longitude }` for resolving the zone; the server persists only `cityId` / `zoneGeohash`.

### Chat sessions

Session detail returns `lastCityId` and `lastZoneGeohash` instead of exact coordinates. The ask request still sends current lat/lon for nearby-site ranking; those values are not stored as precise GPS history.

## Suggested client flow

1. `POST /app-users/guest` or register/login/social.
2. Show consent screens; `PUT /app-users/me/consents`.
3. `POST /mobile/tours/recommend` with current location.
4. `POST /mobile/tours/feedback` (echo `strategyId` when present).
5. `POST /mobile/chat/ask` with `sessionId` continuity.
6. Refresh access token before expiry; on logout revoke refresh token.
7. Support Settings → Export data / Delete account via `/me/export` and `DELETE /me`.

See also: [docs/compliance/P4.4-gdpr-technical.md](compliance/P4.4-gdpr-technical.md).
