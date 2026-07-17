# Restaurants

Source: [`app/routers/restaurants.py`](../app/routers/restaurants.py) · schemas: [`app/schemas.py`](../app/schemas.py)

A `Restaurant` is owned by exactly one `User` (`owner_user_id`, set automatically to whoever is
logged in when they apply). There's no self-serve way to become an **admin** yet - that's a manual
DB flip of `User.is_admin` for now (see [`auth.md`](./auth.md) for what "admin" gates).

Status lifecycle: `pending` (on apply) -> `approved` / `rejected` (by an admin). Re-applying while
`rejected` resets it back to `pending` rather than erroring.

## `POST /restaurants/apply`

Submit (or resubmit) a restaurant application. **Auth:** Bearer token (any logged-in user).

**Body** (`application/json`):

| Field | Type | Constraints |
|---|---|---|
| `name` | string | 1-200 chars |
| `contact_email` | string | valid email - the restaurant's business email, can differ from the owner's login email |
| `address` | string | 1-500 chars |
| `description` | string | 1-2000 chars |

```bash
curl -X POST http://localhost:8000/restaurants/apply \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"name": "Joe'\''s Deli", "contact_email": "biz@joesdeli.com", "address": "1 Main St", "description": "Sandwiches"}'
```

**Response** `200 OK`: a `RestaurantOut` (see below) with `status: "pending"`.

Calling this again for the same logged-in user updates the existing application in place and
resets its status to `pending` - it does not create a second restaurant. This also flips the
caller's `User.account_type` to `"restaurant"`.

---

## `GET /restaurants/me`

The caller's own restaurant, whatever its status. **Auth:** Bearer token, must own a restaurant.

**Response** `200 OK` (`RestaurantOut` - includes fields not shown to the public):
```json
{
  "id": 1, "owner_user_id": 3, "name": "Joe's Deli", "contact_email": "biz@joesdeli.com",
  "address": "1 Main St", "description": "Sandwiches", "status": "pending",
  "rejection_reason": null, "created_at": "2026-07-16T19:34:28Z"
}
```

**Errors:** `404` if the caller has never applied.

---

## `POST /restaurants/{id}/approve` / `POST /restaurants/{id}/reject`

**Auth:** Bearer token, `User.is_admin` must be true (403 otherwise).

Approve takes no body. Reject requires `{"reason": "..."}` (1-500 chars), stored on the restaurant
and returned to the owner via `GET /restaurants/me`. Both return the updated `RestaurantOut`.
Approving clears any previous `rejection_reason`.

```bash
curl -X POST http://localhost:8000/restaurants/1/approve -H "Authorization: Bearer $ADMIN_TOKEN"
curl -X POST http://localhost:8000/restaurants/1/reject -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" -d '{"reason": "Address incomplete"}'
```

**Errors:** `403` if not an admin, `404` if the restaurant id doesn't exist.

---

## `GET /restaurants` / `GET /restaurants/{id}`

Public restaurant directory / profile. **Auth:** none. Only ever returns `approved` restaurants -
`pending`/`rejected` ones 404 on the detail route and are omitted from the list, so there's no way
to probe for an application's existence or status from the outside.

**Response** (`RestaurantPublicOut` - no `owner_user_id`, `contact_email`, or `rejection_reason`):
```json
{ "id": 1, "name": "Joe's Deli", "address": "1 Main St", "description": "Sandwiches" }
```

List route returns `RestaurantPublicOut[]`.
