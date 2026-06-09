import stripe
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from sqlalchemy import select

from .. import schemas
from .. import models
from ..database import get_db
from ..utils.oauth2 import get_current_client
from ..utils.email import send_order_confirmation_email
from ..utils.sms import send_order_confirmation_sms
from datetime import datetime, timezone
from ..config import settings

stripe.api_key = settings.stripe_secret_key

router = APIRouter(prefix="/payments", tags=["Payments"])


# ─── CREATE CHECKOUT SESSION (CLIENT ONLY) ───────────────


@router.post("/checkout/{order_public_id}")
def create_checkout_session(
    order_public_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_client),
):
    # 1. Get the order
    order = db.execute(
        select(models.Order).where(
            models.Order.public_id == order_public_id,
            models.Order.user_id == current_user.id,
        )
    ).scalar_one_or_none()

    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Order not found"
        )

    # 2. Check order is still pending
    if order.status != schemas.OrderStatus.pending:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This order has already been processed",
        )

    # 3. Check if already paid
    existing_payment = db.execute(
        select(models.Payment).where(
            models.Payment.order_id == order.id,
        )
    ).scalar_one_or_none()

    if existing_payment and existing_payment.status == schemas.PaymentStatus.completed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This order has already been paid",
        )

    # 4. Get restaurant name for the checkout page
    restaurant = db.execute(
        select(models.Restaurant).where(models.Restaurant.id == order.restaurant_id)
    ).unique().scalar_one_or_none()

    # 5. Create Stripe checkout session
    try:
        session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            line_items=[
                {
                    "price_data": {
                        "currency": "zar",
                        "product_data": {
                            "name": f"Order from {restaurant.name}",
                            "description": f"Order ID: {str(order.public_id)}",
                        },
                        "unit_amount": int(order.total_price * 100),
                    },
                    "quantity": 1,
                }
            ],
            mode="payment",
            success_url=f"{settings.base_url}/payments/success?order_id={str(order.public_id)}",
            cancel_url=f"{settings.base_url}/payments/cancel?order_id={str(order.public_id)}",
            metadata={
                "order_id": str(order.public_id),
                "user_id": str(current_user.public_id),
            },
        )

        # 6. Save payment to database
        new_payment = models.Payment(
            order_id=order.id,
            user_id=current_user.id,
            amount=order.total_price,
            status=schemas.PaymentStatus.pending,
            stripe_payment_id=session.id,
        )

        db.add(new_payment)
        db.commit()

        # 7. Return checkout URL to frontend
        return {"checkout_url": session.url}

    except stripe.StripeError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


# ─── STRIPE WEBHOOK ───────────────────────────────────────


@router.post("/webhook")
async def stripe_webhook(request: Request, db: Session = Depends(get_db)):
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")

    # 1. Verify webhook signature
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.stripe_webhook_secret
        )
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid payload"
        )
    except stripe.SignatureVerificationError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid signature"
        )

    # 2. Handle checkout session completed
    if event.type == "checkout.session.completed":
        try:
            session = event.data.object
            
            if session.payment_status != "paid":
                return {"message": "Payment not completed"}

            # 3. Get order_id from metadata
            order_public_id = session.metadata["order_id"] if session.metadata else None

            if not order_public_id:
                return {"message": "No order ID in metadata"}

            # 4. Find payment in database
            order = db.execute(
                select(models.Order).where(models.Order.public_id == order_public_id)
            ).scalar_one_or_none()

            if not order:
                return {"message": "Order not found"}

            payment = db.execute(
                select(models.Payment).where(models.Payment.order_id == order.id)
            ).scalar_one_or_none()
            
            #payment: models.Payment
            
            print(f"Order ID: {order.id}")  # ← add this
            print(f"Payment found: {payment}")  # ← add this

            if not payment:
                print("NO PAYMENT FOUND FOR THIS ORDER!")
                return {"message": "Payment not found"}
            
            if payment.status == schemas.PaymentStatus.completed:
                return {"message": "Already processed"}

            if payment.status != schemas.PaymentStatus.completed:
                # 5. Update payment status
                payment.status = schemas.PaymentStatus.completed
                payment.payment_method = "card"

                # 6. Update order status
                order.status = schemas.OrderStatus.confirmed
                order.updated_at = datetime.now(timezone.utc)
                
                db.commit()
                print("Order confirmed successfully!")

                # 7. Get user and restaurant
                user = db.execute(
                    select(models.User).where(models.User.id == payment.user_id)
                ).scalar_one_or_none()

                restaurant = db.execute(
                    select(models.Restaurant).where(
                        models.Restaurant.id == order.restaurant_id
                    )
                ).unique().scalar_one_or_none()

                # 8. Send confirmation email and SMS
                if user and restaurant:
                    try:
                        send_order_confirmation_email(
                            to=user.email,
                            name=user.name,
                            order_id=str(order.public_id),
                            total_price=str(order.total_price),
                            restaurant_name=restaurant.name,
                        )
                    except Exception as e:
                        print(f"Email error: {e}") 
                           
                    try:    
                        send_order_confirmation_sms(
                            to=user.phone_number,
                            name=user.name,
                            total_price=str(order.total_price),
                            restaurant_name=restaurant.name,
                        )
                    except Exception as e:
                        print(f"SMS error: {e}")    

                
        except Exception as e:
            print(f"Webhook error: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=str(e)
            )    

    # 9. Handle failed payment
    elif event.type == "checkout.session.expired":
        session = event.data.object
        order_public_id = session.metadata["order_id"] if session.metadata else None

        if order_public_id:
            order = db.execute(
                select(models.Order).where(models.Order.public_id == order_public_id)
            ).scalar_one_or_none()

            if order:
                payment = db.execute(
                    select(models.Payment).where(models.Payment.order_id == order.id)
                ).scalar_one_or_none()

                if payment:
                    payment.status = schemas.PaymentStatus.failed
                    db.commit()

    return {"message": "Webhook received successfully"}


# ─── PAYMENT SUCCESS ──────────────────────────────────────


@router.get("/success")
def payment_success(
    order_id: str,
    db: Session = Depends(get_db),
   
):
    order = db.execute(
        select(models.Order).where(
            models.Order.public_id == order_id
        )
    ).scalar_one_or_none()

    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Order not found"
        )

    return {
        "message": "Payment received. We are processing your order.",
        "order_id": order_id,
        "status": order.status,
    }


# ─── PAYMENT CANCEL ───────────────────────────────────────


@router.get("/cancel")
def payment_cancel(
    order_id: str,
    db: Session = Depends(get_db),
    
):
    order = db.execute(
        select(models.Order).where(
            models.Order.public_id == order_id
        )
    ).scalar_one_or_none()

    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Order not found"
        )

    return {
        "message": "Checkout was not completed.",
        "order_id": order_id,
        "status": order.status,
    }
