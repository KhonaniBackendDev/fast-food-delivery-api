import resend
from app.config import settings

resend.api_key = settings.resend_api_key


def send_verification_email(to: str, name: str, token: str):
    verification_link = f"{settings.base_url}/verify-email?token={token}"

    if settings.env == "development":
        print(f"EMAIL LINK: {verification_link}")
        return

    resend.Emails.send(
        {
            "from": settings.resend_from_email,
            "to": to,
            "subject": "Verify your email address",
            "html": f"""
            <h2>Welcome {name}!</h2>
            <p>Thank you for registering. Please verify your email address by clicking the link below:</p>
            <a href="{verification_link}" style="
                background-color: #ff4500;
                color: white;
                padding: 12px 24px;
                text-decoration: none;
                border-radius: 5px;
                display: inline-block;
            ">Verify Email</a>
            <p>This link expires in 24 hours.</p>
            <p>If you did not create an account, ignore this email.</p>
        """,
        }
    )


def send_password_reset_email(to: str, name: str, token: str):
    reset_link = f"{settings.frontend_url}/reset-password?token={token}"

    if settings.env == "development":
        print(f"PASSWORD RESET LINK: {reset_link}")
        return
    
    resend.Emails.send(
        {
            "from": settings.resend_from_email,
            "to": to,
            "subject": "Reset your password",
            "html": f"""
            <h2>Hi {name},</h2>
            <p>You requested to reset your password. Click the link below:</p>
            <a href="{reset_link}" style="
                background-color: #ff4500;
                color: white;
                padding: 12px 24px;
                text-decoration: none;
                border-radius: 5px;
                display: inline-block;
            ">Reset Password</a>
            <p>This link expires in 15 minutes.</p>
            <p>If you did not request a password reset, ignore this email.</p>
        """,
        }
    )


def send_order_confirmation_email(
    to: str, name: str, order_id: str, total_price: str, restaurant_name: str
):
    if settings.env == "development":
        print(f"ORDER CONFIRMATION EMAIL: would be sent to {to}")
        return
    
    resend.Emails.send(
        {
            "from": settings.resend_from_email,
            "to": to,
            "subject": "Order Confirmed!",
            "html": f"""
            <h2>Hi {name}, your order has been confirmed!</h2>
            <p>Here are your order details:</p>
            <ul>
                <li><strong>Order ID:</strong> {order_id}</li>
                <li><strong>Restaurant:</strong> {restaurant_name}</li>
                <li><strong>Total:</strong> R{total_price}</li>
            </ul>
            <p>Your food is being prepared. We will notify you when it is on its way!</p>
        """,
        }
    )


def send_welcome_email(to: str, name: str):
    
    if settings.env == "development":
        print(f"WELCOME")
        return
    
    resend.Emails.send(
        {
            "from": settings.resend_from_email,
            "to": to,
            "subject": "Welcome! Your account is now active 🎉",
            "html": f"""
            <h2>Welcome {name}! 🎉</h2>
            <p>Your account has been fully verified and is now active.</p>
            <p>You can now browse restaurants and place orders.</p>
            <p>Enjoy your meal!</p>
        """,
        }
    )


def send_password_changed_email(to: str, name: str):
    
    if settings.env == "development":
        print(f"PASSWORD CHANGED EMAIL: would be sent to {to}")
        return
    
    resend.Emails.send(
        
        {
            "from": settings.resend_from_email,
            "to": to,
            "subject": "Your password has been changed",
            "html": f"""
            <h2>Hi {name},</h2>
            <p>Your password was successfully changed.</p>
            <p>If you did not make this change please contact us immediately.</p>
        """,
        }
    )


def send_order_out_for_delivery_email(
    to: str, name: str, restaurant_name: str, order_id: str
):
    if settings.env == "development":
        print(f"OUT FOR DELIVERY EMAIL: would be sent to {to}")
        return
    
    resend.Emails.send(
        {
            "from": settings.resend_from_email,
            "to": to,
            "subject": "Your order is on the way! 🚗",
            "html": f"""
            <h2>Hi {name},</h2>
            <p>Great news! Your order from {restaurant_name} is on its way to you.</p>
            <p>Your order ID is: {order_id}</p>
            <p>The driver is heading your way. Please make sure someone is available to receive the order.</p>
        """,
        }
    )


def send_order_delivered_email(to: str, name: str, restaurant_name: str, order_id: str):
    
    if settings.env == "development":
        print(f"ORDER DELIVERED EMAIL: would be sent to {to}")
        return
    
    resend.Emails.send(
        {
            "from": settings.resend_from_email,
            "to": to,
            "subject": "Your order has been delivered! 🎉",
            "html": f"""
            <h2>Hi {name},</h2>
            <p>Your order from {restaurant_name} has been delivered!</p>
            <p>Your order ID is: {order_id}</p>
            <p>We hope you enjoy your meal!</p>
            <p>Don't forget to rate your experience.</p>
        """,
        }
    )
