# Auth

Source: [`app/routers/auth.py`](../app/routers/auth.py) · schemas: [`app/schemas.py`](../app/schemas.py)

## `POST /auth/register`

Creates an account. **Auth:** none.

**Body** (`application/json`):

| Field      | Type   | Constraints                          |
|------------|--------|---------------------------------------|
| `username` | string | 3-50 chars, must be unique            |
| `email`    | string | valid email, must be unique           |
| `password` | string | 8-128 chars (only first 72 bytes are actually used by bcrypt) |

```bash
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username": "matt", "email": "matt@example.com", "password": "supersecret1"}'
```

```ts
await fetch("http://localhost:8000/auth/register", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({ username: "matt", email: "matt@example.com", password: "supersecret1" }),
});
```

**Response** `201 Created`:
```json
{ "id": 1, "username": "matt", "email": "matt@example.com", "account_type": "customer", "created_at": "2026-07-16T19:34:28Z" }
```

**Errors**
| Status | When |
|---|---|
| `400` | `{"detail": "Username already taken"}` or `{"detail": "Email already registered"}` |
| `422` | body failed validation (bad email format, password too short, etc.) |

---

## `POST /auth/login`

Exchanges username + password for a JWT. **Auth:** none.

Unlike every other endpoint, this one takes an **OAuth2 password form**
(`application/x-www-form-urlencoded`), not JSON - that's a FastAPI/OAuth2 convention
(`OAuth2PasswordRequestForm`), so the interactive `/docs` "Authorize" button works out of the box.

**Body** (form-encoded):

| Field      | Type   | Notes |
|------------|--------|-------|
| `username` | string | required |
| `password` | string | required |

```bash
curl -X POST http://localhost:8000/auth/login \
  -d "username=matt&password=supersecret1"
```

```ts
const form = new URLSearchParams({ username: "matt", password: "supersecret1" });
const res = await fetch("http://localhost:8000/auth/login", { method: "POST", body: form });
const { access_token } = await res.json();
```

**Response** `200 OK`:
```json
{ "access_token": "eyJhbGciOi...", "token_type": "bearer" }
```

Store `access_token` (e.g. in memory or `localStorage`) and send it as
`Authorization: Bearer <access_token>` on subsequent requests.

**Errors**
| Status | When |
|---|---|
| `401` | `{"detail": "Incorrect username or password"}` |

---

## `GET /auth/me`

Returns the logged-in user's profile. **Auth:** Bearer token.

```bash
curl http://localhost:8000/auth/me -H "Authorization: Bearer $TOKEN"
```

```ts
await fetch("http://localhost:8000/auth/me", {
  headers: { Authorization: `Bearer ${accessToken}` },
});
```

**Response** `200 OK`:
```json
{ "id": 1, "username": "matt", "email": "matt@example.com", "account_type": "customer", "created_at": "2026-07-16T19:34:28Z" }
```

**Errors**
| Status | When |
|---|---|
| `401` | missing/expired/invalid token |

Useful for checking "is this user still logged in" on app load - if it 401s, drop the stored
token and send them back to login.

## `account_type`

Every user starts as `"customer"`. It flips to `"restaurant"` automatically the first time they
call `POST /restaurants/apply` (see [`restaurants.md`](./restaurants.md)) - there's no separate
"sign up as a restaurant" flow, and no field for it on `POST /auth/register`. There's also a
separate `is_admin` flag (not exposed on `UserOut`) that gates restaurant approval/rejection -
there's no self-serve way to become an admin yet, it's a manual DB update.
