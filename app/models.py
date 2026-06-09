from app.database import Base
from sqlalchemy import (
    Column,
    BigInteger,
    String,
    Integer,
    text,
    TIMESTAMP,
    Boolean,
    Enum,
    ForeignKey,
    Numeric,
)
from sqlalchemy.dialects.postgresql import UUID
import uuid
from app.enumz import UserRole, OrderStatus, PaymentStatus, TokenType
from sqlalchemy.orm import relationship


class User(Base):
    __tablename__ = "users"

    id = Column(BigInteger, primary_key=True, nullable=False, index=True)
    public_id = Column(
        UUID(as_uuid=True), default=uuid.uuid4, unique=True, nullable=False
    )
    name = Column(String, nullable=False)
    email = Column(String, nullable=False, unique=True)
    phone_number = Column(String, nullable=False, unique=True)
    password = Column(String, nullable=False)
    role = Column(Enum(UserRole), nullable=False)
    image_url = Column(String, nullable=True)
    is_email_verified = Column(Boolean, default=False, nullable=False)
    is_phone_verified = Column(Boolean, default=False, nullable=False)
    is_verified = Column(Boolean, default=False, nullable=False)
    failed_attempts = Column(Integer, server_default="0", nullable=False)
    locked_until = Column(TIMESTAMP(timezone=True), nullable=True)
    created_at = Column(
        TIMESTAMP(timezone=True), server_default=text("now()"), nullable=False
    )


class Address(Base):
    __tablename__ = "addresses"

    id = Column(BigInteger, primary_key=True, nullable=False, index=True)
    public_id = Column(
        UUID(as_uuid=True), default=uuid.uuid4, unique=True, nullable=False
    )
    user_id = Column(BigInteger, ForeignKey("users.id"), nullable=False)
    street = Column(String, nullable=False)
    city = Column(String, nullable=False)
    state = Column(String, nullable=True)
    province = Column(String, nullable=True)
    country = Column(String, nullable=False)
    postal_code = Column(String, nullable=False)
    is_default = Column(Boolean, default=False, nullable=False)
    created_at = Column(
        TIMESTAMP(timezone=True), server_default=text("now()"), nullable=False
    )


class Restaurant(Base):
    __tablename__ = "restaurants"

    id = Column(BigInteger, primary_key=True, nullable=False, index=True)
    public_id = Column(
        UUID(as_uuid=True), default=uuid.uuid4, unique=True, nullable=False
    )
    user_id = Column(BigInteger, ForeignKey("users.id"), nullable=False)
    name = Column(String, nullable=False)
    description = Column(String, nullable=True)
    phone_number = Column(String, nullable=False)
    address = Column(String, nullable=False)
    is_open = Column(Boolean, default=True, nullable=False)
    image_url = Column(String, nullable=True)
    created_at = Column(
        TIMESTAMP(timezone=True), server_default=text("now()"), nullable=False
    )
    # Relationships
    ratings = relationship("Rating", back_populates="restaurant", lazy="joined")


class Food(Base):
    __tablename__ = "foods"

    id = Column(BigInteger, primary_key=True, nullable=False, index=True)
    public_id = Column(
        UUID(as_uuid=True), default=uuid.uuid4, unique=True, nullable=False
    )
    restaurant_id = Column(BigInteger, ForeignKey("restaurants.id"), nullable=False)
    name = Column(String, nullable=False)
    description = Column(String, nullable=True)
    price = Column(Numeric(precision=10, scale=2), nullable=False)
    is_available = Column(Boolean, default=True, nullable=False)
    image_url = Column(String, nullable=True)
    created_at = Column(
        TIMESTAMP(timezone=True), server_default=text("now()"), nullable=False
    )
    


class Order(Base):
    __tablename__ = "orders"

    id = Column(BigInteger, primary_key=True, nullable=False, index=True)
    public_id = Column(
        UUID(as_uuid=True), default=uuid.uuid4, unique=True, nullable=False
    )
    user_id = Column(BigInteger, ForeignKey("users.id"), nullable=False)
    restaurant_id = Column(BigInteger, ForeignKey("restaurants.id"), nullable=False)
    address_id = Column(BigInteger, ForeignKey("addresses.id"), nullable=False)
    status = Column(Enum(OrderStatus), nullable=False)
    total_price = Column(Numeric(precision=10, scale=2), nullable=False)
    created_at = Column(
        TIMESTAMP(timezone=True), server_default=text("now()"), nullable=False
    )
    updated_at = Column(
        TIMESTAMP(timezone=True), server_default=text("now()"), nullable=False
    )


class OrderItem(Base):
    __tablename__ = "order_items"

    id = Column(BigInteger, primary_key=True, nullable=False, index=True)
    public_id = Column(
        UUID(as_uuid=True), default=uuid.uuid4, unique=True, nullable=False
    )
    order_id = Column(BigInteger, ForeignKey("orders.id"), nullable=False)
    food_id = Column(BigInteger, ForeignKey("foods.id"), nullable=False)
    quantity = Column(Integer, nullable=False)
    price = Column(Numeric(precision=10, scale=2), nullable=False)


class Rating(Base):
    __tablename__ = "ratings"

    id = Column(BigInteger, primary_key=True, nullable=False, index=True)
    public_id = Column(
        UUID(as_uuid=True), default=uuid.uuid4, unique=True, nullable=False
    )
    user_id = Column(BigInteger, ForeignKey("users.id"), nullable=False)
    restaurant_id = Column(BigInteger, ForeignKey("restaurants.id"), nullable=False)
    rating = Column(Numeric(precision=2, scale=1), nullable=False)
    review = Column(String, nullable=True)
    created_at = Column(
        TIMESTAMP(timezone=True), server_default=text("now()"), nullable=False
    )
    # Relationships
    restaurant = relationship("Restaurant", back_populates="ratings")


class Payment(Base):
    __tablename__ = "payments"

    id = Column(BigInteger, primary_key=True, nullable=False, index=True)
    public_id = Column(
        UUID(as_uuid=True), default=uuid.uuid4, unique=True, nullable=False
    )
    order_id = Column(BigInteger, ForeignKey("orders.id"), nullable=False)
    user_id = Column(BigInteger, ForeignKey("users.id"), nullable=False)
    amount = Column(
        Numeric(precision=10, scale=2), nullable=False, default=PaymentStatus.pending
    )
    status = Column(Enum(PaymentStatus), nullable=False)
    payment_method = Column(String, nullable=True)
    stripe_payment_id = Column(String, nullable=True)
    created_at = Column(
        TIMESTAMP(timezone=True), server_default=text("now()"), nullable=False
    )


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    id = Column(BigInteger, primary_key=True, nullable=False, index=True)
    public_id = Column(
        UUID(as_uuid=True), default=uuid.uuid4, unique=True, nullable=False
    )
    user_id = Column(BigInteger, ForeignKey("users.id"), nullable=False)
    token = Column(String, nullable=False, unique=True)
    expires_at = Column(TIMESTAMP(timezone=True), nullable=False)
    created_at = Column(
        TIMESTAMP(timezone=True), server_default=text("now()"), nullable=False
    )


class VerificationToken(Base):
    __tablename__ = "verification_tokens"

    id = Column(BigInteger, primary_key=True, nullable=False, index=True)
    public_id = Column(
        UUID(as_uuid=True), default=uuid.uuid4, unique=True, nullable=False
    )
    user_id = Column(BigInteger, ForeignKey("users.id"), nullable=False)
    token = Column(String, nullable=False, unique=True)
    type = Column(Enum(TokenType), nullable=False)
    expires_at = Column(TIMESTAMP(timezone=True), nullable=False)
    is_used = Column(Boolean, default=False, nullable=False)
    created_at = Column(
        TIMESTAMP(timezone=True), server_default=text("now()"), nullable=False
    )
