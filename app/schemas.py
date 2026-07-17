from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, model_validator


class UserCreate(BaseModel):
    username: str = Field(min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    email: EmailStr
    account_type: str
    created_at: datetime


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class CheckoutSessionCreate(BaseModel):
    amount: int = Field(gt=0, description="Amount in the smallest currency unit, e.g. cents")
    currency: str = Field(default="usd", min_length=3, max_length=3)
    description: str | None = Field(default=None, max_length=500)


class CheckoutSessionOut(BaseModel):
    checkout_url: str
    session_id: str


class PaymentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    amount: int
    currency: str
    status: str
    description: str | None
    created_at: datetime


class RestaurantApplicationInput(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    contact_email: EmailStr
    address: str = Field(min_length=1, max_length=500)
    description: str = Field(min_length=1, max_length=2000)


class RestaurantOut(BaseModel):
    """Full detail - for the owner viewing their own restaurant, or an admin."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    owner_user_id: int
    name: str
    contact_email: EmailStr
    address: str
    description: str
    status: str
    rejection_reason: str | None
    created_at: datetime


class RestaurantPublicOut(BaseModel):
    """What customers see - no owner account info or internal rejection reason."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    address: str
    description: str


class RestaurantRejectRequest(BaseModel):
    reason: str = Field(min_length=1, max_length=500)


class ListingInput(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str = Field(min_length=1, max_length=2000)
    original_price: int = Field(gt=0, description="Cents")
    discounted_price: int = Field(gt=0, description="Cents")
    quantity_available: int = Field(ge=0)
    pickup_window: str = Field(min_length=1, max_length=200)

    @model_validator(mode="after")
    def discounted_not_above_original(self) -> "ListingInput":
        if self.discounted_price > self.original_price:
            raise ValueError("discounted_price cannot be greater than original_price")
        return self


class ListingOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    restaurant_id: int
    restaurant_name: str
    title: str
    description: str
    original_price: int
    discounted_price: int
    quantity_available: int
    pickup_window: str
    created_at: datetime


class OrderCreate(BaseModel):
    listing_id: int
    quantity: int = Field(default=1, ge=1)


class OrderOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    listing_id: int
    listing_title: str
    restaurant_name: str
    pickup_window: str
    quantity: int
    price: int
    status: str
    created_at: datetime


class OrderCreateOut(BaseModel):
    order: OrderOut
    checkout_url: str
    session_id: str


class OrderStatusUpdate(BaseModel):
    status: Literal["ready", "picked_up", "cancelled"]
