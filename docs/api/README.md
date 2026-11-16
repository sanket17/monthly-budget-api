# Personal Budget API: integration guide

For the mobile (and web) client developers.

| File | What it is |
|---|---|
| [`openapi.yaml`](openapi.yaml) | OpenAPI 3 reference: every endpoint, field, enum, example body and error. Import into Swagger Editor, Postman, Insomnia, or use it to generate a client (`openapi-generator`, `swagger-codegen`, Dart/Kotlin/Swift generators). |
| [`postman/Personal-Budget-API.postman_collection.json`](postman/Personal-Budget-API.postman_collection.json) | Postman collection: all 46 requests with headers, example bodies, saved example responses, and scripts that capture tokens and ids. |
| [`postman/production.postman_environment.json`](postman/production.postman_environment.json), [`local.postman_environment.json`](postman/local.postman_environment.json) | Environments (`baseUrl`, tokens, ids). |
| Live Swagger UI | https://api.paise-kuthe-gele.com/api/schema/swagger-ui/ (raw schema: `/api/schema/`) |

**Base URL:** `https://api.paise-kuthe-gele.com` (local: `http://localhost:8000`). Every path ends with a trailing slash.

## Try it in Postman (2 minutes)

1. Import the collection and one environment, then select the environment (top right).
2. Run **Auth → Register**, then **Auth → Log in**. Tokens are stored automatically.
3. Run **Categories → List categories** to see the 49 default categories, then
   **Create transaction**, and so on. Create requests save the new id
   (`{{transactionId}}`, ...) so follow-up requests work without editing.
4. Tokens refresh automatically before they expire (collection pre-request script).

## Headers

| Header | Value | When |
|---|---|---|
| `Content-Type` | `application/json` | requests with a body |
| `Accept` | `application/json` | always (recommended) |
| `Authorization` | `Bearer <access token>` | every endpoint except Register, Log in, Refresh, Log out |

## Authentication flow

```
Register  POST /api/auth/register/            -> 201 user
Log in    POST /api/auth/login/               -> 200 {access, refresh}
   ... use  Authorization: Bearer <access>  on every call ...
On 401    POST /api/auth/token/refresh/       -> 200 {access, refresh}   (store BOTH)
          refresh fails (401)                 -> send the user to the login screen
Log out   POST /api/auth/logout/ {refresh}    -> 200 {}    (then delete both tokens)
```

- Access token: **60 minutes**. Refresh token: **7 days**.
- Refresh tokens **rotate**: each refresh returns a *new* `refresh` and revokes the
  one you sent. Always overwrite the stored refresh token. Never refresh from two
  places at once (e.g. two parallel requests both seeing a 401): queue them behind one
  refresh call.
- Keep tokens in the platform's secure storage (iOS Keychain, Android Keystore /
  EncryptedSharedPreferences), never in plain preferences or logs.
- Register and Log in are limited to **5 requests/minute per IP** (429 beyond that).
  Other endpoints: 1000 requests/day per user.

## Conventions

- **Money** is a decimal **string**: `"450.00"`. Parse with a decimal type, never a float.
- **Dates** are `YYYY-MM-DD`. **Month** query values are `YYYY-MM` (`YYYY-MM-DD` is accepted and
  normalised to the 1st). Timestamps are ISO 8601 UTC (`2026-03-15T09:30:00Z`).
- **Month window**: `GET /api/transactions/` and `GET /api/credit-card-entries/` return one
  calendar month (`?month=`, default = current month). Fetching a single item by id works for any month.
- **Pagination** (transactions and credit-card entries only):
  `?page=1&page_size=20` (max 100) returns `{ "count", "next", "previous", "results": [...] }`.
  All other list endpoints return a plain JSON array.
- **Soft delete**: deleting a category, credit card or recurring entry hides it but keeps its
  history. `DELETE` returns `204` with no body.
- **User timezone** (set at registration, editable in profile) decides what "today" means for
  recurring entries.
- A category's `category_type` is `expense` or `income`. Expense categories have a `group`
  (`needs`, `wants`, `investment`, `other`); income categories have none.

## Errors

| Status | Body | Meaning |
|---|---|---|
| 400 | `{"amount": ["Amount must be greater than zero."]}` | Validation: keys are field names, values are lists of messages. |
| 400 | `{"month": "Must be in YYYY-MM or YYYY-MM-DD format."}` | Same, but the value can be a plain **string** (invalid `?month=`). |
| 400 | `["Cannot delete a category referenced by ..."]` | A few business-rule errors are a bare **array** of messages. |
| 401 | `{"detail": "Authentication credentials were not provided."}` or `{"detail": "...", "code": "token_not_valid"}` | No/invalid/expired access token, or wrong login. |
| 404 | `{"detail": "Not found."}` | No such id, or it belongs to another user. |
| 429 | `{"detail": "Request was throttled. Expected available in N seconds."}` | Rate limit. |

A client should therefore accept all three 400 shapes: an object of `field -> string | string[]`,
or an array of strings. Show field errors next to the form field and bare messages as a general error.

## Typical screens → calls

| Screen | Calls |
|---|---|
| Onboarding | Register → Log in → *Initial balances: Set* (bank) |
| Home / dashboard | `GET /api/dashboard/?month=2026-03` (one call: balances, savings, group breakdown, totals) |
| Add expense | `GET /api/categories/` (once, cache) → `POST /api/transactions/` |
| Month list | `GET /api/transactions/?month=2026-03&page=1` |
| Budget planning | `GET /api/categories/?month=...` (shows `planned_amount`) → `POST /api/planned-amounts/` |
| Credit cards | `GET /api/credit-cards/?month=...` (planned vs `actual_amount`), `GET /api/credit-card-entries/?month=...&card=<id>` |
| Recurring | `GET/POST /api/recurring-entries/`, `POST /api/recurring-entries/generate/` |

## Keeping these files current

The files here are **generated** from the code. After changing an endpoint, serializer, or
`config/api_docs.py`:

```bash
python scripts/build_api_docs.py          # regenerate
python scripts/build_api_docs.py --check  # CI-style freshness check
```

The test suite replays the whole Postman collection against the real API (every example
body must be accepted, every documented response must match) and fails if these files are
out of date.
