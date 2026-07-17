import stripe
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.deps import get_current_user
from app.models import Payment, User
from app.schemas import CheckoutSessionCreate, CheckoutSessionOut, PaymentOut

router = APIRouter(prefix="/payments", tags=["payments"])

stripe.api_key = settings.stripe_secret_key


def _get_or_create_stripe_customer(user: User, db: Session) -> str:
    if user.stripe_customer_id:
        return user.stripe_customer_id

    customer = stripe.Customer.create(email=user.email, name=user.username)
    user.stripe_customer_id = customer.id
    db.commit()
    return customer.id


@router.post("/checkout-session", response_model=CheckoutSessionOut)
def create_checkout_session(
    payload: CheckoutSessionCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    customer_id = _get_or_create_stripe_customer(current_user, db)

    session = stripe.checkout.Session.create(
        mode="payment",
        payment_method_types=["card"],
        customer=customer_id,
        line_items=[
            {
                "price_data": {
                    "currency": payload.currency,
                    "product_data": {"name": payload.description or "FreshForward order"},
                    "unit_amount": payload.amount,
                },
                "quantity": 1,
            }
        ],
        success_url=f"{settings.frontend_url}/payment/success?session_id={{CHECKOUT_SESSION_ID}}",
        cancel_url=f"{settings.frontend_url}/payment/cancel",
        metadata={"user_id": str(current_user.id)},
    )

    payment = Payment(
        user_id=current_user.id,
        stripe_checkout_session_id=session.id,
        amount=payload.amount,
        currency=payload.currency,
        description=payload.description,
        status="pending",
    )
    db.add(payment)
    db.commit()

    return CheckoutSessionOut(checkout_url=session.url, session_id=session.id)


@router.post("/webhook", status_code=status.HTTP_200_OK)
async def stripe_webhook(request: Request, db: Session = Depends(get_db)):
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature", "")

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, settings.stripe_webhook_secret)
    except (ValueError, stripe.SignatureVerificationError):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid webhook payload")

    event_type = event["type"]
    data = event["data"]["object"]

    if event_type == "checkout.session.completed":
        payment = (
            db.query(Payment).filter(Payment.stripe_checkout_session_id == data["id"]).first()
        )
        if payment:
            payment.status = "succeeded"
            payment.stripe_payment_intent_id = data.get("payment_intent")
            db.commit()

    elif event_type in ("checkout.session.expired", "checkout.session.async_payment_failed"):
        payment = (
            db.query(Payment).filter(Payment.stripe_checkout_session_id == data["id"]).first()
        )
        if payment:
            payment.status = "failed"
            db.commit()

    return {"received": True}


@router.get("/history", response_model=list[PaymentOut])
def payment_history(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    return (
        db.query(Payment)
        .filter(Payment.user_id == current_user.id)
        .order_by(Payment.created_at.desc())
        .all()
    )
