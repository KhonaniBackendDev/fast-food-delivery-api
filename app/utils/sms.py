from twilio.rest import Client
from ..config import settings

client = Client(settings.twilio_account_sid, settings.twilio_auth_token)


def send_sms(to: str, body: str):
    if settings.env == "development":
        print(f"\n[DEV SMS]")
        print(f"To: {to}")
        print(f"Message: {body}")
        print("─" * 50)
        return

    try:
        client.messages.create(
            body=body,
            from_=settings.twilio_phone_number,
            to=to
        )
    except Exception as e:
        print(f"[SMS ERROR] Failed to send SMS to {to}: {e}")

def send_phone_verification_sms(to: str, code: str):
    if settings.env == "development":
        print(f"SMS CODE: {code}")
        return

    client.messages.create(
        body=f"Your verification code is: {code}. This code expires in 10 minutes. Do not share this with anyone.",
        from_=settings.twilio_phone_number,
        to=to,
    )


def send_order_status_sms(to: str, name: str, status: str, restaurant_name: str):
    client.messages.create(
        body=f"Hi {name}, your order from {restaurant_name} is now {status}.",
        from_=settings.twilio_phone_number,
        to=to,
    )


def send_order_confirmation_sms(
    to: str, name: str, total_price: str, restaurant_name: str
):
    client.messages.create(
        body=f"Hi {name}, your order from {restaurant_name} has been received! Total: R{total_price}. We will keep you updated.",
        from_=settings.twilio_phone_number,
        to=to,
    )


def send_order_delivered_sms(to: str, name: str, restaurant_name: str):
    client.messages.create(
        body=f"Hi {name}, your order from {restaurant_name} has been delivered! Enjoy your meal! 🎉",
        from_=settings.twilio_phone_number,
        to=to,
    )
