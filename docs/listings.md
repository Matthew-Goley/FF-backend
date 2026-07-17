# Listings

Source: [`app/routers/listings.py`](../app/routers/listings.py) · schemas: [`app/schemas.py`](../app/schemas.py)

All prices are integers in **cents** (same convention as [`payments.md`](./payments.md) - `500` =
$5.00), to avoid float rounding issues.

## `GET /listings` / `GET /listings/{id}`

Public browse/detail. **Auth:** none. Only shows listings belonging to `approved` restaurants -
a listing from a `pending`/`rejected` restaurant 404s on the detail route and is omitted from the
list.

**Response** (`ListingOut`):
```json
{
  "id": 5, "restaurant_id": 1, "restaurant_name": "Joe's Deli",
  "title": "Sandwich", "description": "Turkey club", "original_price": 1000,
  "discounted_price": 500, "quantity_available": 3, "pickup_window": "5-6pm",
  "created_at": "2026-07-16T19:34:28Z"
}
```
List route returns `ListingOut[]`.

---

## `GET /restaurants/me/listings`

The caller's own listings. **Auth:** Bearer token, caller must own an **approved** restaurant
(`404` if no restaurant at all, `403` if it exists but isn't approved yet - see
[`restaurants.md`](./restaurants.md)).

---

## `POST /restaurants/me/listings`

Create a listing under the caller's own (approved) restaurant. **Auth:** same as above.

**Body** (`ListingInput`):

| Field | Type | Constraints |
|---|---|---|
| `title` | string | 1-200 chars |
| `description` | string | 1-2000 chars |
| `original_price` | int | cents, > 0 |
| `discounted_price` | int | cents, > 0, **must be <= `original_price`** (422 otherwise) |
| `quantity_available` | int | >= 0 |
| `pickup_window` | string | 1-200 chars, free text (e.g. `"5-6pm"`) |

`restaurant_id` and `restaurant_name` are derived server-side from the caller's own restaurant -
don't send them.

**Response** `201 Created`: the new `ListingOut`.

---

## `PUT /restaurants/me/listings/{id}` / `DELETE /restaurants/me/listings/{id}`

Update or delete a listing. **Auth:** same as create, plus ownership - `403` if the listing
belongs to a different restaurant than the caller's. `PUT` takes the same body as create (full
replace, not a partial patch) and returns the updated `ListingOut`; `DELETE` returns `204`.

**Errors**
| Status | When |
|---|---|
| `403` | listing exists but belongs to another restaurant |
| `404` | no listing with that id |
| `400` (delete only) | the listing has orders against it - deleting it would orphan order history, so it's blocked. There's no archive/soft-delete yet; set `quantity_available` to `0` instead if you just want it to stop showing up as purchasable. |

Deleting a listing does **not** currently check whether `quantity_available` has ever been ordered
via a separate flag - the check is "does any `Order` row reference this listing," which is the
same thing in practice.
