import enum


class UserRole(str, enum.Enum):
    owner = "owner"
    client = "client"


class OrderStatus(str, enum.Enum):
    pending = "pending"
    confirmed = "confirmed"
    preparing = "preparing"
    out_for_delivery = "out_for_delivery"
    delivered = "delivered"
    cancelled = "cancelled"


class PaymentStatus(str, enum.Enum):
    pending = "pending"
    completed = "completed"
    failed = "failed"
    refunded = "refunded"


class TokenType(str, enum.Enum):
    password_reset = "password_reset"
    email_verification = "email_verification"
    phone_verification = "phone_verification"
