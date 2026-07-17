# Orders

Source: [`app/routers/orders.py`](../app/routers/orders.py) · schemas: [`app/schemas.py`](../app/schemas.py)

Placing an order creates the `Order` row **and** a Stripe Checkout Session in one call - it
doesn't charge synchronously. Status is updated later by the Stripe webhook (payment result) and
by the owning restaurant (fulfillment progress). See [`payments.md`](./payments.md) for the
underlying Stripe flow this reuses.

**Status lifecycle:**
```
pending_payment --(webhook: checkout.session.completed)--> paid
pending_payment --(webhook: checkout.session.expired / async_payment_failed)--> payment_failed
paid --(restaurant, PATCH .../status)--> ready --> picked_up
paid or ready --(restaurant, PATCH .../status)--> cancelled
```
`pending_payment`, `paid`, and `payment_failed` are set **only** by the Stripe webhook - the
restaurant-facing status endpoint below rejects any attempt to set them directly (422, not just a
convention). `payment_failed` and `cancelled` both restore the listing's `quantity_available`.
Cancelling a `paid` order does **not** automatically refund the Stripe payment - there's no refund
handler yet, that'd need a manual `stripe.Refund.create` call.

## `POST /orders`

Place an order. **Auth:** Bearer token (any logged-in user - no restaurant/customer distinction
needed here).

**Body** (`OrderCreate`):

| Field | Type | Constraints |
|---|---|---|
| `listing_id` | int | must exist and belong to an `approved` restaurant (404 otherwise) |
| `quantity` | int | >= 1, defaults to `1`. Must be <= the listing's current `quantity_available` |

```ts
const res = await fetch("http://localhost:8000/orders", {
  method: "POST",
  headers: { "Content-Type": "application/json", Authorization: `Bearer ${accessToken}` },
  body: JSON.stringify({ listing_id: 5, quantity: 2 }),
});
const { order, checkout_url } = await res.json();
window.location.href = checkout_url;
```

**Response** `201 Created` (`OrderCreateOut`):
```json
{
  "order": {
    "id": 12, "listing_id": 5, "listing_title": "Sandwich", "restaurant_name": "Joe's Deli",
    "pickup_window": "5-6pm", "quantity": 2, "price": 1000, "status": "pending_payment",
    "created_at": "2026-07-16T19:34:28Z"
  },
  "checkout_url": "https://checkout.stripe.com/c/pay/cs_test_...",
  "session_id": "cs_test_..."
}
```
`price` is `discounted_price * quantity`, in cents. Redirect the browser to `checkout_url` exactly
like the standalone payments flow.

`quantity_available` on the listing is decremented **immediately** on order creation (reserved,
not just at payment success) so two customers can't both buy the last unit while one has an
unpaid Stripe session open. If the Stripe API call itself fails, the whole thing (order + stock
decrement) is rolled back and nothing is created.

**Errors**
| Status | When |
|---|---|
| `400` | not enough `quantity_available` left |
| `401` | missing/invalid token |
| `404` | no such listing, or its restaurant isn't approved |
| `502` | Stripe API call failed - order was not placed |

---

## `GET /orders/{id}`

**Auth:** Bearer token. Only the customer who placed it, or the owning restaurant, can view it -
`403` for anyone else, `404` if the id doesn't exist. Response shape matches the `order` object
above (`OrderOut`).

---

## `GET /restaurants/me/orders`

All orders against the caller's own restaurant, newest first. **Auth:** Bearer token, caller must
own an **approved** restaurant (same gating as the listings-CRUD endpoints in
[`listings.md`](./listings.md)). Returns `OrderOut[]`.

---

## `PATCH /orders/{id}/status`

Advance an order's fulfillment status. **Auth:** Bearer token, caller must be the owning
restaurant (`404`/`403` per the same restaurant-ownership rules as above).

**Body** (`OrderStatusUpdate`):
```json
{ "status": "ready" }
```
`status` must be one of `"ready"`, `"picked_up"`, `"cancelled"` - anything else (including
`"paid"` or `"pending_payment"`) is rejected at the schema level with `422`, not just ignored.

**Errors**
| Status | When |
|---|---|
| `400` | the transition isn't legal from the order's current status (e.g. `paid` -> `picked_up` directly, or touching an order that's still `pending_payment`) |
| `403` | caller's restaurant doesn't own this order |
| `404` | no such order |
| `422` | `status` isn't one of the three allowed values |
