from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import select

from .. import schemas
from .. import models
from ..database import get_db
from ..utils.oauth2 import get_current_owner, get_current_client
from ..utils.email import send_order_out_for_delivery_email, send_order_delivered_email
from ..utils.sms import send_order_status_sms, send_order_delivered_sms
from uuid import UUID
from decimal import Decimal
from datetime import datetime, timezone
import httpx
from ..utils.sms import send_order_status_sms
from ..enumz import OrderStatus, PaymentStatus

router = APIRouter(prefix="/orders", tags=["Orders"])


# ─── CREATE ORDER (CLIENT ONLY) ──────────────────────────


@router.post(
    "/", status_code=status.HTTP_201_CREATED
)
def create_order(
    order_data: schemas.OrderCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_client),
):
    # 1. Verify restaurant exists and is open
    restaurant = (
        db.execute(
            select(models.Restaurant).where(
                models.Restaurant.public_id == order_data.restaurant_public_id
            )
        )
        .unique()
        .scalar_one_or_none()
    )

    if not restaurant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Restaurant not found"
        )

    if not restaurant.is_open:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Restaurant is currently closed",
        )
        
    # Check if client already has a pending unpaid order
    existing_pending_order = db.execute(
        select(models.Order).where(
            models.Order.user_id == current_user.id,
            models.Order.status == OrderStatus.pending
        )
    ).scalar_one_or_none()

    if existing_pending_order:
        # Check if payment exists and is completed
        existing_payment = db.execute(
            select(models.Payment).where(
                models.Payment.order_id == existing_pending_order.id,
                models.Payment.status == PaymentStatus.completed
            )
        ).scalar_one_or_none()

        if not existing_payment:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="You already have a pending order. Please complete or cancel it before placing a new one"
            )    

    # 2. Verify delivery address belongs to client
    address = db.execute(
        select(models.Address).where(
            models.Address.public_id == order_data.address_public_id,
            models.Address.user_id == current_user.id,
        )
    ).scalar_one_or_none()

    if not address:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Delivery address not found"
        )

    # 3. Verify all food items and calculate total price
    total_price = Decimal("0.00")
    order_items_to_create = []

    for item in order_data.items:
        food = db.execute(
            select(models.Food).where(
                models.Food.public_id == item.food_public_id,
                models.Food.restaurant_id == restaurant.id,
            )
        ).scalar_one_or_none()

        if not food:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=f"Food item not found"
            )

        if not food.is_available:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"{food.name} is currently unavailable",
            )

        # Calculate price for this item
        item_total = food.price * item.quantity
        total_price += item_total

        order_items_to_create.append(
            {"food_id": food.id, "quantity": item.quantity, "price": item_total}
        )

    # 4. Create the order
    new_order = models.Order(
        user_id=current_user.id,
        restaurant_id=restaurant.id,
        address_id=address.id,
        status=schemas.OrderStatus.pending,
        total_price=total_price,
    )

    db.add(new_order)
    db.flush()  # flush so new_order.id is available without committing yet

    # 5. Create all order items
    for item_data in order_items_to_create:
        order_item = models.OrderItem(
            order_id=new_order.id,
            food_id=item_data["food_id"],
            quantity=item_data["quantity"],
            price=item_data["price"],
        )
        db.add(order_item)

    db.commit()
    db.refresh(new_order)
    
    # After db.commit() and db.refresh(new_order)

# Get order items with food details
    order_items = db.execute(
        select(models.OrderItem).where(
            models.OrderItem.order_id == new_order.id
        )
    ).scalars().all()

    # Build items response
    items_response = []
    for item in order_items:
        food = db.execute(
            select(models.Food).where(models.Food.id == item.food_id)
        ).scalar_one()
        
        items_response.append({
            "public_id": item.public_id,
            "food_public_id": food.public_id,
            "food_name": food.name,
            "quantity": item.quantity,
            "price": item.price
        })

    # Return full response
    return {
        "public_id": new_order.public_id,
        "restaurant_name": restaurant.name,
        "restaurant_public_id": restaurant.public_id,
        "address_public_id": address.public_id,
        "status": new_order.status,
        "total_price": new_order.total_price,
        "items": items_response,
        "created_at": new_order.created_at,
        "updated_at": new_order.updated_at
    }

    


# ─── GET MY ORDERS (CLIENT ONLY) ─────────────────────────


@router.get("/me")
def get_my_orders(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_client),
):
    orders = (
        db.execute(
            select(models.Order)
            .where(models.Order.user_id == current_user.id)
            .order_by(models.Order.created_at.desc())
            .limit(15)
        )
        .scalars()
        .all()
    )
    
    result = []
    for order in orders:
        restaurant = db.execute(
            select(models.Restaurant).where(
                models.Restaurant.id == order.restaurant_id
            )
        ).unique().scalar_one_or_none()

        address = db.execute(
            select(models.Address).where(
                models.Address.id == order.address_id
            )
        ).scalar_one_or_none()

        order_items = db.execute(
            select(models.OrderItem).where(
                models.OrderItem.order_id == order.id
            )
        ).scalars().all()

        items_response = []
        for item in order_items:
            food = db.execute(
                select(models.Food).where(models.Food.id == item.food_id)
            ).scalar_one()

            items_response.append({
                "public_id": item.public_id,
                "food_public_id": food.public_id,
                "food_name": food.name,
                "quantity": item.quantity,
                "price": item.price
            })

        result.append({
            "public_id": order.public_id,
            "restaurant_name": restaurant.name if restaurant else "Unknown",
            "restaurant_public_id": restaurant.public_id if restaurant else None,
            "address_public_id": address.public_id if address else None,
            "status": order.status,
            "total_price": order.total_price,
            "items": items_response,
            "created_at": order.created_at,
            "updated_at": order.updated_at
        })

    return result


# ─── GET ONE ORDER (CLIENT ONLY) ─────────────────────────


@router.get("/me/{order_public_id}")
def get_one_order(
    order_public_id: UUID,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_client),
):
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
        
    restaurant = db.execute(
        select(models.Restaurant).where(
            models.Restaurant.id == order.restaurant_id
        )
    ).scalar_one_or_none()

    address = db.execute(
        select(models.Address).where(
            models.Address.id == order.address_id
        )
    ).scalar_one_or_none()

    order_items = db.execute(
        select(models.OrderItem).where(
            models.OrderItem.order_id == order.id
        )
    ).scalars().all()

    items_response = []
    for item in order_items:
        food = db.execute(
            select(models.Food).where(models.Food.id == item.food_id)
        ).scalar_one()

        items_response.append({
            "public_id": item.public_id,
            "food_public_id": food.public_id,
            "food_name": food.name,
            "quantity": item.quantity,
            "price": item.price
        })

    return {
        "public_id": order.public_id,
        "restaurant_name": restaurant.name if restaurant else "Unknown",
        "restaurant_public_id": restaurant.public_id if restaurant else None,
        "address_public_id": address.public_id if address else None,
        "status": order.status,
        "total_price": order.total_price,
        "items": items_response,
        "created_at": order.created_at,
        "updated_at": order.updated_at
    }    

    


# ─── GET RESTAURANT ORDERS (OWNER ONLY) ──────────────────


@router.get("/restaurant", response_model=list[schemas.OrderResponse])
def get_restaurant_orders(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_owner),
):
    # 1. Get owner's restaurant
    restaurant = (
        db.execute(
            select(models.Restaurant).where(
                models.Restaurant.user_id == current_user.id
            )
        )
        .unique()
        .scalar_one_or_none()
    )

    if not restaurant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="You do not have a restaurant yet",
        )

    # 2. Get all orders for that restaurant
    orders = (
        db.execute(
            select(models.Order).where(models.Order.restaurant_id == restaurant.id)
        )
        .scalars()
        .all()
    )

    if not orders:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="There are no orders at the moment",
        )

    return orders


# ─── UPDATE ORDER STATUS (OWNER ONLY) ────────────────────


@router.patch("/{order_public_id}/status", response_model=schemas.OrderResponse)
async def update_order_status(
    order_public_id: UUID,
    status_data: schemas.OrderStatusUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_owner),
):
    # 1. Get owner's restaurant
    restaurant = db.execute(
        select(models.Restaurant).where(models.Restaurant.user_id == current_user.id)
    ).unique().scalar_one_or_none()

    if not restaurant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="You do not have a restaurant yet",
        )

    # 2. Find the order and make sure it belongs to their restaurant
    order = db.execute(
        select(models.Order).where(
            models.Order.public_id == order_public_id,
            models.Order.restaurant_id == restaurant.id,
        )
    ).scalar_one_or_none()

    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Order not found"
        )

    # 3. Get the user who placed the order
    user = db.execute(
        select(models.User).where(models.User.id == order.user_id)
    ).scalar_one_or_none()

    # 4. Update status
    order.status = status_data.status
    order.updated_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(order)

    # 5. Send email based on status
    if user:
        
        try:
            if status_data.status == OrderStatus.out_for_delivery:
                send_order_out_for_delivery_email(
                    to=user.email,
                    name=user.name,
                    restaurant_name=restaurant.name,
                    order_id=str(order.public_id),
                )

            elif status_data.status == OrderStatus.delivered:
                send_order_delivered_email(
                    to=user.email,
                    name=user.name,
                    restaurant_name=restaurant.name,
                    order_id=str(order.public_id),
                )
                # Add this ↓
                send_order_delivered_sms(
                    to=user.phone_number, name=user.name, restaurant_name=restaurant.name
                )

            # 6. Send SMS update
            send_order_status_sms(
                to=user.phone_number,
                name=user.name,
                status=status_data.status.value,
                restaurant_name=restaurant.name,
            )
        except Exception as e:
            print(f"Email error: {e}")
    # Notify client via WebSocket
    try:
        async with httpx.AsyncClient() as client:
            await client.post(
                f"http://localhost:8000/tracking/notify/{str(order_public_id)}"
            )
    except Exception:
        pass  # Don't fail if notification fails

    return order


# ─── REORDER (CLIENT ONLY) ───────────────────────────────


@router.post(
    "/reorder/{order_public_id}",
    status_code=status.HTTP_201_CREATED,
)
def reorder(
    order_public_id: UUID,
    reorder_data: schemas.ReorderRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_client),
):
    # 1. Find the old order and make sure it belongs to this client
    old_order = db.execute(
        select(models.Order).where(
            models.Order.public_id == order_public_id,
            models.Order.user_id == current_user.id,
        )
    ).scalar_one_or_none()

    if not old_order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Order not found"
        )

    # 2. Check the restaurant is still open
    restaurant = db.execute(
        select(models.Restaurant).where(models.Restaurant.id == old_order.restaurant_id)
    ).scalar_one_or_none()

    if not restaurant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Restaurant no longer exists"
        )

    if not restaurant.is_open:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Restaurant is currently closed",
        )

    # 3. Determine delivery address
    # If client sent a new address use it, otherwise use the original
    if reorder_data.address_public_id:
        address = db.execute(
            select(models.Address).where(
                models.Address.public_id == reorder_data.address_public_id,
                models.Address.user_id == current_user.id,
            )
        ).scalar_one_or_none()

        if not address:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Delivery address not found",
            )
    else:
        # Use the same address as the original order
        address = db.execute(
            select(models.Address).where(models.Address.id == old_order.address_id)
        ).scalar_one_or_none()

        if not address:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Original delivery address no longer exists. Please provide a new address",
            )

    # 4. Get old order items
    old_order_items = (
        db.execute(
            select(models.OrderItem).where(models.OrderItem.order_id == old_order.id)
        )
        .scalars()
        .all()
    )

    # 5. Verify all food items and recalculate prices
    total_price = Decimal("0.00")
    order_items_to_create = []
    unavailable_items = []

    for old_item in old_order_items:
        food = db.execute(
            select(models.Food).where(models.Food.id == old_item.food_id)
        ).scalar_one_or_none()

        if not food or not food.is_available:
            unavailable_items.append(old_item.food_id)
            continue

        item_total = food.price * old_item.quantity
        total_price += item_total

        order_items_to_create.append(
            {"food_id": food.id, "quantity": old_item.quantity, "price": item_total}
        )

    # 6. If any items are unavailable tell the client
    if unavailable_items:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"{len(unavailable_items)} item(s) from your original order are no longer available",
        )

    # 7. Create the new order
    new_order = models.Order(
        user_id=current_user.id,
        restaurant_id=restaurant.id,
        address_id=address.id,
        status=schemas.OrderStatus.pending,
        total_price=total_price,
    )

    db.add(new_order)
    db.flush()

    # 8. Create new order items
    for item_data in order_items_to_create:
        order_item = models.OrderItem(
            order_id=new_order.id,
            food_id=item_data["food_id"],
            quantity=item_data["quantity"],
            price=item_data["price"],
        )
        db.add(order_item)

    db.commit()
    db.refresh(new_order)
    
    # 9. Build full response
    order_items = db.execute(
        select(models.OrderItem).where(
            models.OrderItem.order_id == new_order.id
        )
    ).scalars().all()

    items_response = []
    for item in order_items:
        food = db.execute(
            select(models.Food).where(models.Food.id == item.food_id)
        ).scalar_one()

        items_response.append({
            "public_id": item.public_id,
            "food_public_id": food.public_id,
            "food_name": food.name,
            "quantity": item.quantity,
            "price": item.price
        })

    return {
        "public_id": new_order.public_id,
        "restaurant_name": restaurant.name,
        "restaurant_public_id": restaurant.public_id,
        "address_public_id": address.public_id,
        "status": new_order.status,
        "total_price": new_order.total_price,
        "items": items_response,
        "created_at": new_order.created_at,
        "updated_at": new_order.updated_at
    }

    


# ─── CANCEL ORDER (CLIENT ONLY) ──────────────────────────

@router.patch("/me/{order_public_id}/cancel", response_model=schemas.OrderResponse)
def cancel_order(
    order_public_id: UUID,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_client)
):
    # 1. Find the order
    order = db.execute(
        select(models.Order).where(
            models.Order.public_id == order_public_id,
            models.Order.user_id == current_user.id
        )
    ).scalar_one_or_none()

    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found"
        )

    # 2. Check if order can be cancelled
    if order.status != OrderStatus.pending:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Order cannot be cancelled. Current status is {order.status.value}. You can only cancel pending orders"
        )

    # 3. Check if payment already made
    existing_payment = db.execute(
        select(models.Payment).where(
            models.Payment.order_id == order.id,
            models.Payment.status == PaymentStatus.completed
        )
    ).scalar_one_or_none()

    if existing_payment:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Order cannot be cancelled. Payment has already been completed"
        )

    # 4. Cancel the order
    order.status = OrderStatus.cancelled
    order.updated_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(order)

    return order
