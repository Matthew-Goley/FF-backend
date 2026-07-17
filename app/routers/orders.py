import stripe
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.deps import get_current_restaurant, get_current_user
from app.models import Listing, Order, Payment, Restaurant, User
from app.routers.payments import _get_or_create_stripe_customer
from app.schemas import OrderCreate, OrderCreateOut, OrderOut, OrderStatusUpdate

router = APIRouter(tags=["orders"])

# restaurant-driven transitions only; pending_payment -> paid/payment_failed come from the Stripe webhook
_ALLOWED_TRANSITIONS: dict[str, set[str]] = {
    "paid": {"ready", "cancelled"},
    "ready": {"picked_up", "cancelled"},
}


@router.post("/orders", response_model=OrderCreateOut, status_code=status.HTTP_201_CREATED)
def place_order(
    payload: OrderCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    listing = db.get(Listing, payload.listing_id)
    if listing is None or listing.restaurant.status != "approved":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Listing not found")

    if listing.quantity_available < payload.quantity:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Not enough stock available")

    # Get/create the Stripe customer first - safe to commit even if order placement fails below
    customer_id = _get_or_create_stripe_customer(current_user, db)

    listing.quantity_available -= payload.quantity
    price = listing.discounted_price * payload.quantity
    order = Order(
        listing_id=listing.id,
        customer_user_id=current_user.id,
        quantity=payload.quantity,
        price=price,
        status="pending_payment",
    )
    db.add(order)
    db.flush()  # assign order.id without committing, so a Stripe failure below can roll everything back

    try:
        session = stripe.checkout.Session.create(
            mode="payment",
            payment_method_types=["card"],
            customer=customer_id,
            line_items=[
                {
                    "price_data": {
                        "currency": "usd",
                        "product_data": {"name": f"{listing.title} x{payload.quantity}"},
                        "unit_amount": listing.discounted_price,
                    },
                    "quantity": payload.quantity,
                }
            ],
            success_url=f"{settings.frontend_url}/payment/success?session_id={{CHECKOUT_SESSION_ID}}",
            cancel_url=f"{settings.frontend_url}/payment/cancel",
            metadata={"user_id": str(current_user.id), "order_id": str(order.id)},
        )
    except stripe.StripeError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY, detail="Payment provider error, order not placed"
        )

    db.add(
        Payment(
            user_id=current_user.id,
            order_id=order.id,
            stripe_checkout_session_id=session.id,
            amount=price,
            currency="usd",
            description=f"{listing.title} x{payload.quantity}",
            status="pending",
        )
    )
    db.commit()
    db.refresh(order)

    return OrderCreateOut(order=order, checkout_url=session.url, session_id=session.id)


def _restaurant_id_for(current_user: User, db: Session) -> int | None:
    restaurant = db.query(Restaurant).filter(Restaurant.owner_user_id == current_user.id).first()
    return restaurant.id if restaurant else None


@router.get("/orders/{order_id}", response_model=OrderOut)
def read_order(
    order_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    order = db.get(Order, order_id)
    if order is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")

    is_customer = order.customer_user_id == current_user.id
    is_owning_restaurant = order.listing.restaurant_id == _restaurant_id_for(current_user, db)
    if not (is_customer or is_owning_restaurant):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not your order")

    return order


@router.get("/restaurants/me/orders", response_model=list[OrderOut])
def read_my_restaurant_orders(
    restaurant: Restaurant = Depends(get_current_restaurant), db: Session = Depends(get_db)
):
    return (
        db.query(Order)
        .join(Listing)
        .filter(Listing.restaurant_id == restaurant.id)
        .order_by(Order.created_at.desc())
        .all()
    )


@router.patch("/orders/{order_id}/status", response_model=OrderOut)
def update_order_status(
    order_id: int,
    payload: OrderStatusUpdate,
    restaurant: Restaurant = Depends(get_current_restaurant),
    db: Session = Depends(get_db),
):
    order = db.get(Order, order_id)
    if order is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
    if order.listing.restaurant_id != restaurant.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not your order")

    allowed = _ALLOWED_TRANSITIONS.get(order.status, set())
    if payload.status not in allowed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot move an order from '{order.status}' to '{payload.status}'",
        )

    if payload.status == "cancelled":
        # Return the reserved stock. Note: this does NOT refund the Stripe payment automatically -
        # that still needs a manual/future stripe.Refund.create call.
        order.listing.quantity_available += order.quantity

    order.status = payload.status
    db.commit()
    db.refresh(order)
    return order
