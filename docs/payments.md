# Payments

Source: [`app/routers/payments.py`](../app/routers/payments.py) · schemas: [`app/schemas.py`](../app/schemas.py)

Payment model for v1: FreshForward's Stripe account collects the full charge through a Stripe
**Checkout Session**. There's no Stripe Connect / marketplace split yet - restaurant payouts
aren't handled by this API (still an open product decision, see `productscope.md` in the
frontend repo).

## `POST /payments/checkout-session`

Creates a Stripe Checkout Session and a matching `pending` `Payment` row. **Auth:** Bearer token.

**Body** (`application/json`):

| Field         | Type   | Constraints |
|---------------|--------|-------------|
| `amount`      | int    | required, > 0, **in the smallest currency unit** (cents for USD - `1000` = $10.00) |
| `currency`    | string | optional, 3-letter ISO code, defaults to `"usd"` |
| `description` | string | optional, up to 500 chars - shown on the Stripe Checkout page as the line-item name |

```bash
curl -X POST http://localhost:8000/payments/checkout-session \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"amount": 1500, "currency": "usd", "description": "Order #42 - Joe'\''s Deli"}'
```

```ts
const res = await fetch("http://localhost:8000/payments/checkout-session", {
  method: "POST",
  headers: {
    "Content-Type": "application/json",
    Authorization: `Bearer ${accessToken}`,
  },
  body: JSON.stringify({ amount: 1500, currency: "usd", description: "Order #42 - Joe's Deli" }),
});
const { checkout_url } = await res.json();
window.location.href = checkout_url; // hand off to Stripe-hosted checkout page
```

**Response** `200 OK`:
```json
{ "checkout_url": "https://checkout.stripe.com/c/pay/cs_test_...", "session_id": "cs_test_..." }
```

Redirect the browser to `checkout_url` - don't try to build a custom card form against this
endpoint, Stripe hosts the payment page. On completion Stripe redirects the user back to:
- success: `{FRONTEND_URL}/payment/success?session_id={CHECKOUT_SESSION_ID}`
- cancel: `{FRONTEND_URL}/payment/cancel`

Those two frontend routes don't exist yet - they're placeholders baked into the redirect URLs
this endpoint builds (see `settings.frontend_url` in [`app/config.py`](../app/config.py)), and
still need to be built as actual pages. Nothing else in the backend depends on their exact path,
so they can be renamed as long as this endpoint's redirect URLs are updated to match. The actual
`Payment.status` update on success comes from the **webhook** below, not from the user landing on
the success page - don't treat arriving at `/payment/success` as proof the charge went through.

**Errors**
| Status | When |
|---|---|
| `401` | missing/invalid token |
| `422` | body failed validation (e.g. `amount <= 0`) |
| `500` | Stripe API call failed (bad/missing `STRIPE_SECRET_KEY`, Stripe outage, etc.) - not yet caught and turned into a clean error response |

---

## `POST /payments/webhook`

Stripe calls this directly - the frontend never calls it. **Auth:** Stripe signature
(`Stripe-Signature` header), verified against `STRIPE_WEBHOOK_SECRET`.

Configure in the Stripe dashboard: endpoint URL `<api-url>/payments/webhook`, subscribed to:
- `checkout.session.completed` -> marks the matching `Payment` `succeeded`, stores `stripe_payment_intent_id`
- `checkout.session.expired` -> marks it `failed`
- `checkout.session.async_payment_failed` -> marks it `failed`

Other event types are accepted (returns `200`) but ignored. There's no handler yet for refunds -
`status` can currently only end up as `pending`, `succeeded`, or `failed`, even though the
`Payment.status` column comment mentions `refunded` as a possible future value.

**Response**: always `{"received": true}` on success. `400` if the signature doesn't verify
(wrong/missing `STRIPE_WEBHOOK_SECRET`, or the request didn't actually come from Stripe).

---

## `GET /payments/history`

Lists the current user's payments, newest first. **Auth:** Bearer token.

```bash
curl http://localhost:8000/payments/history -H "Authorization: Bearer $TOKEN"
```

```ts
await fetch("http://localhost:8000/payments/history", {
  headers: { Authorization: `Bearer ${accessToken}` },
});
```

**Response** `200 OK`:
```json
[
  {
    "id": 1,
    "amount": 1500,
    "currency": "usd",
    "status": "succeeded",
    "description": "Order #42 - Joe's Deli",
    "created_at": "2026-07-16T19:34:28Z"
  }
]
```

**Errors**
| Status | When |
|---|---|
| `401` | missing/invalid token |
