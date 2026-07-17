# FreshForward API docs

Reference for calling the backend from the frontend (or curl/Postman). One page per domain:

- [`auth.md`](./auth.md) - register, login, current user
- [`restaurants.md`](./restaurants.md) - apply, approve/reject, public directory
- [`listings.md`](./listings.md) - public browse, owner CRUD
- [`orders.md`](./orders.md) - place an order, fulfillment status
- [`payments.md`](./payments.md) - Stripe checkout, webhook, payment history

FastAPI also serves interactive, always-up-to-date docs at `/docs` (Swagger UI) and `/redoc`
whenever the server is running - these markdown pages are a faster-to-read companion, not a
replacement.

## Base URL

| Environment | URL |
|---|---|
| Local dev   | `http://localhost:8000` |
| Production  | your Railway service URL (see `README.md` "Deploying on Railway") |

Every path below is relative to that base, e.g. `POST /auth/login` means
`POST http://localhost:8000/auth/login` locally.

## Authentication

Endpoints marked **Auth: Bearer token** require an `Authorization` header:

```
Authorization: Bearer <access_token>
```

Get a token from `POST /auth/login` (see [`auth.md`](./auth.md)). Tokens are JWTs signed with
`SECRET_KEY` and expire after `ACCESS_TOKEN_EXPIRE_MINUTES` (defaults to 24h) - after that, the
user has to log in again to get a new one. There is currently no refresh-token flow.

## Request / response format

All request bodies and responses are JSON (`Content-Type: application/json`), **except**
`POST /auth/login`, which takes `application/x-www-form-urlencoded` (OAuth2 password form) -
see [`auth.md`](./auth.md) for why.

## Errors

Two shapes, depending on what went wrong:

**Validation errors** (missing/malformed fields - HTTP 422), from Pydantic/FastAPI automatically:
```json
{
  "detail": [
    { "loc": ["body", "email"], "msg": "value is not a valid email address", "type": "value_error" }
  ]
}
```

**Application errors** (bad credentials, duplicate username, etc. - HTTP 400/401), raised
explicitly by our route handlers:
```json
{ "detail": "Incorrect username or password" }
```

Check the status code first, then read `detail` - its shape depends on which of the two cases
you hit.
