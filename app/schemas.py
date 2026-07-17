from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserCreate(BaseModel):
    username: str = Field(min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    email: EmailStr
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
