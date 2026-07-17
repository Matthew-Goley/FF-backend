from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    stripe_customer_id: Mapped[str | None] = mapped_column(String(255), unique=True, nullable=True)

    # "customer" | "restaurant" - flipped to "restaurant" by POST /restaurants/apply
    account_type: Mapped[str] = mapped_column(String(20), default="customer", nullable=False)
    # No self-serve way to become an admin yet - flip this manually in the DB for now
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)

    payments: Mapped[list["Payment"]] = relationship(back_populates="user")
    orders: Mapped[list["Order"]] = relationship(back_populates="customer")
    restaurant: Mapped["Restaurant | None"] = relationship(back_populates="owner", uselist=False)


class Restaurant(Base):
    __tablename__ = "restaurants"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    owner_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), unique=True, nullable=False)

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    contact_email: Mapped[str] = mapped_column(String(255), nullable=False)
    address: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str] = mapped_column(String(2000), nullable=False)

    status: Mapped[str] = mapped_column(String(20), default="pending", nullable=False)  # pending|approved|rejected
    rejection_reason: Mapped[str | None] = mapped_column(String(500), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False
    )

    owner: Mapped["User"] = relationship(back_populates="restaurant")
    listings: Mapped[list["Listing"]] = relationship(back_populates="restaurant")


class Listing(Base):
    __tablename__ = "listings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    restaurant_id: Mapped[int] = mapped_column(ForeignKey("restaurants.id"), nullable=False, index=True)

    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(String(2000), nullable=False)
    original_price: Mapped[int] = mapped_column(Integer, nullable=False)  # cents
    discounted_price: Mapped[int] = mapped_column(Integer, nullable=False)  # cents
    quantity_available: Mapped[int] = mapped_column(Integer, nullable=False)
    pickup_window: Mapped[str] = mapped_column(String(200), nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False
    )

    restaurant: Mapped["Restaurant"] = relationship(back_populates="listings")
    orders: Mapped[list["Order"]] = relationship(back_populates="listing")

    @property
    def restaurant_name(self) -> str:
        return self.restaurant.name


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    listing_id: Mapped[int] = mapped_column(ForeignKey("listings.id"), nullable=False, index=True)
    customer_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)

    quantity: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    price: Mapped[int] = mapped_column(Integer, nullable=False)  # cents, snapshot of listing price * quantity

    # pending_payment -> paid -> ready -> picked_up, or cancelled / payment_failed.
    # pending_payment/paid/payment_failed are set only by the Stripe webhook; ready/picked_up/cancelled
    # are set by the owning restaurant via PATCH /orders/:id/status.
    status: Mapped[str] = mapped_column(String(20), default="pending_payment", nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False
    )

    listing: Mapped["Listing"] = relationship(back_populates="orders")
    customer: Mapped["User"] = relationship(back_populates="orders")
    payment: Mapped["Payment | None"] = relationship(back_populates="order", uselist=False)

    @property
    def listing_title(self) -> str:
        return self.listing.title

    @property
    def restaurant_name(self) -> str:
        return self.listing.restaurant.name

    @property
    def pickup_window(self) -> str:
        return self.listing.pickup_window


class Payment(Base):
    __tablename__ = "payments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    order_id: Mapped[int | None] = mapped_column(ForeignKey("orders.id"), unique=True, nullable=True)

    stripe_checkout_session_id: Mapped[str | None] = mapped_column(String(255), unique=True, nullable=True)
    stripe_payment_intent_id: Mapped[str | None] = mapped_column(String(255), unique=True, nullable=True)

    amount: Mapped[int] = mapped_column(Integer, nullable=False)  # smallest currency unit, e.g. cents
    currency: Mapped[str] = mapped_column(String(3), default="usd", nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="pending", nullable=False)  # pending|succeeded|failed|refunded
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False
    )

    user: Mapped["User"] = relationship(back_populates="payments")
    order: Mapped["Order | None"] = relationship(back_populates="payment")
