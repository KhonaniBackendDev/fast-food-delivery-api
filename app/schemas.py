from pydantic import BaseModel, EmailStr, Field, field_validator
from app.enumz import UserRole, OrderStatus, PaymentStatus
from datetime import datetime
from uuid import UUID
from typing import Optional
from decimal import Decimal
import re


def validate_password_strength(value: str) -> str:
    if len(value) < 8:
        raise ValueError("Password must be at least 8 characters long")
    if not re.search(r"[A-Z]", value):
        raise ValueError("Password must contain at least one uppercase letter")
    if not re.search(r"[a-z]", value):
        raise ValueError("Password must contain at least one lowercase letter")
    if not re.search(r"\d", value):
        raise ValueError("Password must contain at least one number")
    if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", value):
        raise ValueError("Password must contain at least one special character")
    return value


#      USERS
class UserCreate(BaseModel):
    name: str
    email: EmailStr
    phone_number: str
    password: str
    role: UserRole

    @field_validator("password")
    @classmethod
    def validate_password(cls, value):
        return validate_password_strength(value)


class UserResponse(BaseModel):
    public_id: UUID
    name: str
    email: EmailStr
    phone_number: str
    role: UserRole
    image_url: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


# Used ONLY after registration
class UserRegisterResponse(BaseModel):
    user: UserResponse
    access_token: str
    refresh_token: str
    token_type: str

    class Config:
        from_attributes = True


#      ADDRESS
class AddressCreate(BaseModel):
    street: str
    city: str
    state: Optional[str] = None
    province: Optional[str] = None
    country: str
    postal_code: str
    is_default: bool = False


class AddressResponse(BaseModel):
    public_id: UUID
    street: str
    city: str
    state: Optional[str] = None
    province: Optional[str] = None
    country: str
    postal_code: str
    is_default: bool
    created_at: datetime

    class Config:
        from_attributes = True


class AddressUpdate(BaseModel):
    street: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    province: Optional[str] = None
    country: Optional[str] = None
    postal_code: Optional[str] = None
    is_default: Optional[bool] = None


#      RESTAURANT
class RestaurantCreate(BaseModel):
    name: str
    description: Optional[str] = None
    phone_number: str
    address: str
    is_open: bool = True
    image_url: Optional[str] = None


class RestaurantResponse(BaseModel):
    public_id: UUID
    name: str
    description: Optional[str] = None
    phone_number: str
    address: str
    is_open: bool
    image_url: Optional[str] = None
    average_rating: Optional[float] = None
    total_ratings: Optional[int] = None
    created_at: datetime

    class Config:
        from_attributes = True


class RestaurantUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    phone_number: Optional[str] = None
    address: Optional[str] = None
    is_open: Optional[bool] = None
    image_url: Optional[str] = None


#     FOOD
class FoodCreate(BaseModel):
    name: str
    description: Optional[str] = None
    price: Decimal = Field(gt=Decimal("0"), decimal_places=2, max_digits=10)
    is_available: bool = True
    image_url: Optional[str] = None


class FoodUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    price: Optional[Decimal] = None
    is_available: Optional[bool] = None
    image_url: Optional[str] = None


class FoodResponse(BaseModel):
    public_id: UUID
    name: str
    description: Optional[str] = None
    price: Decimal
    is_available: bool
    image_url: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


#       ORDER ITEM
class OrderItemCreate(BaseModel):
    food_public_id: UUID
    quantity: int = Field(gt=0)


#       ORDER
class OrderCreate(BaseModel):
    restaurant_public_id: UUID
    address_public_id: UUID
    items: list[OrderItemCreate]


class OrderItemResponse(BaseModel):
    public_id: UUID
    quantity: int
    price: Decimal

    class Config:
        from_attributes = True


class OrderResponse(BaseModel):
    public_id: UUID
    status: OrderStatus
    total_price: Decimal
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


#      ORDERSTATUS
class OrderStatusUpdate(BaseModel):
    status: OrderStatus


#     RE-ORDER
class ReorderRequest(BaseModel):
    address_public_id: Optional[UUID] = None


#     RATING
class RatingCreate(BaseModel):
    restaurant_public_id: UUID
    rating: float = Field(ge=0.5, le=5.0)
    review: Optional[str] = None


class RatingResponse(BaseModel):
    public_id: UUID
    rating: float
    review: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


#     RATING UPDATE
class RatingUpdate(BaseModel):
    rating: Optional[float] = Field(None, ge=0.5, le=5.0)
    review: Optional[str] = None


#      PAYMENT
class PaymentResponse(BaseModel):
    public_id: UUID
    order_public_id: UUID
    amount: Decimal
    status: PaymentStatus
    payment_method: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


#    TOKEN
class TokenData(BaseModel):
    id: str


class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str


#    PROFILE
class ProfileUpdate(BaseModel):
    name: Optional[str] = None
    phone_number: Optional[str] = None
    email: Optional[EmailStr] = None
    image_url: Optional[str] = None


class ChangePassword(BaseModel):
    current_password: str
    new_password: str
    confirm_password: str

    @field_validator("new_password")
    @classmethod
    def validate_new_password(cls, value):
        return validate_password_strength(value)


class VerifyPhone(BaseModel):
    code: str


class ForgotPassword(BaseModel):
    email: EmailStr


class ResetPassword(BaseModel):
    token: str
    new_password: str
    confirm_password: str

    @field_validator("new_password")
    @classmethod
    def validate_new_password(cls, value):
        return validate_password_strength(value)

class LogoutRequest(BaseModel):
    refresh_token: str