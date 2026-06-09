from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import select, func

from .. import schemas
from .. import models
from ..database import get_db
from ..utils.oauth2 import get_current_client, get_current_user
from uuid import UUID

router = APIRouter(prefix="/ratings", tags=["Ratings"])


# ─── CREATE RATING (CLIENT ONLY) ─────────────────────────


@router.post(
    "/", response_model=schemas.RatingResponse, status_code=status.HTTP_201_CREATED
)
def create_rating(
    rating_data: schemas.RatingCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_client),
):
    # 1. Check the restaurant exists
    restaurant = (
        db.execute(
            select(models.Restaurant).where(
                models.Restaurant.public_id == rating_data.restaurant_public_id
            )
        )
        .unique()
        .scalar_one_or_none()
    )

    if not restaurant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Restaurant not found"
        )

    # 2. Check client has a delivered order from this restaurant
    delivered_order = db.execute(
        select(models.Order).where(
            models.Order.user_id == current_user.id,
            models.Order.restaurant_id == restaurant.id,
            models.Order.status == schemas.OrderStatus.delivered,
        )
    ).scalar_one_or_none()

    if not delivered_order:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only rate a restaurant after you have a delivered order from them",
        )

    # 3. Check client hasn't already rated this restaurant
    existing_rating = db.execute(
        select(models.Rating).where(
            models.Rating.user_id == current_user.id,
            models.Rating.restaurant_id == restaurant.id,
        )
    ).scalar_one_or_none()

    if existing_rating:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="You have already rated this restaurant. You can update your existing rating",
        )

    # 4. Create the rating
    new_rating = models.Rating(
        user_id=current_user.id,
        restaurant_id=restaurant.id,
        rating=rating_data.rating,
        review=rating_data.review,
    )

    db.add(new_rating)
    db.commit()
    db.refresh(new_rating)

    return new_rating


# ─── GET ALL RATINGS FOR A RESTAURANT (EVERYONE) ─────────


@router.get("/{restaurant_public_id}", response_model=list[schemas.RatingResponse])
def get_restaurant_ratings(
    restaurant_public_id: UUID,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    # 1. Check restaurant exists
    restaurant = (
        db.execute(
            select(models.Restaurant).where(
                models.Restaurant.public_id == restaurant_public_id
            )
        )
        .unique()
        .scalar_one_or_none()
    )

    if not restaurant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Restaurant not found"
        )

    # 2. Get all ratings for that restaurant
    ratings = (
        db.execute(
            select(models.Rating)
            .where(models.Rating.restaurant_id == restaurant.id)
            .order_by(models.Rating.created_at.desc())
        )
        .scalars()
        .all()
    )
    
    if not ratings:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No ratings yet :("
        )

    return ratings


# ─── UPDATE YOUR RATING (CLIENT ONLY) ────────────────────


@router.patch("/{rating_public_id}", response_model=schemas.RatingResponse)
def update_rating(
    rating_public_id: UUID,
    rating_data: schemas.RatingUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_client),
):
    # 1. Find the rating and make sure it belongs to this client
    rating = db.execute(
        select(models.Rating).where(
            models.Rating.public_id == rating_public_id,
            models.Rating.user_id == current_user.id,
        )
    ).scalar_one_or_none()

    if not rating:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Rating not found"
        )

    # 2. Update only what was sent
    update_data = rating_data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(rating, key, value)

    db.commit()
    db.refresh(rating)

    return rating


# ─── DELETE YOUR RATING (CLIENT ONLY) ────────────────────


@router.delete("/{rating_public_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_rating(
    rating_public_id: UUID,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_client),
):
    # 1. Find the rating and make sure it belongs to this client
    rating = db.execute(
        select(models.Rating).where(
            models.Rating.public_id == rating_public_id,
            models.Rating.user_id == current_user.id,
        )
    ).scalar_one_or_none()

    if not rating:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Rating not found"
        )

    db.delete(rating)
    db.commit()
