from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.orm import Session
from sqlalchemy import select, func

from .. import schemas
from .. import models
from ..database import get_db
from app.utils.oauth2 import get_current_owner, get_current_client
from ..utils.cloudinary import upload_image, delete_image
import cloudinary.utils

router = APIRouter(prefix="/restaurants", tags=["Restaurants"])


# ─── CREATE RESTAURANT (OWNER ONLY) ─────────────────────


@router.post(
    "/", response_model=schemas.RestaurantResponse, status_code=status.HTTP_201_CREATED
)
def create_restaurant(
    restaurant_data: schemas.RestaurantCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_owner),
):
    # 1. Check if owner already has a restaurant
    existing_restaurant = (
        db.execute(
            select(models.Restaurant).where(
                models.Restaurant.user_id == current_user.id
            )
        )
        .unique()
        .scalar_one_or_none()
    )

    if existing_restaurant:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="You already have a restaurant"
        )

    # 2. Create restaurant
    new_restaurant = models.Restaurant(
        user_id=current_user.id,
        name=restaurant_data.name,
        description=restaurant_data.description,
        phone_number=restaurant_data.phone_number,
        address=restaurant_data.address,
        is_open=restaurant_data.is_open,
    )

    db.add(new_restaurant)
    db.commit()
    db.refresh(new_restaurant)

    return new_restaurant


# ─── GET MY RESTAURANT (OWNER ONLY) ─────────────────────


@router.get("/me", response_model=schemas.RestaurantResponse)
def get_my_restaurant(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_owner),
):
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

    return restaurant


# ─── GET ALL RESTAURANTS (CLIENT ONLY) ──────────────────


@router.get("/", response_model=list[schemas.RestaurantResponse])
def get_all_restaurants(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_client),
):
    results = (
        db.execute(
            select(
                models.Restaurant,
                func.avg(models.Rating.rating).label("average_rating"),
                func.count(models.Rating.id).label("total_ratings"),
            )
            .outerjoin(
                models.Rating, models.Rating.restaurant_id == models.Restaurant.id
            )
            .where(models.Restaurant.is_open == True)
            .group_by(models.Restaurant.id)
            .order_by(models.Restaurant.created_at.desc())
        )
        .unique()
        .all()
    )

    # Build response manually since we have extra calculated fields
    restaurants = []
    for restaurant, average_rating, total_ratings in results:
        restaurant: models.Restaurant
        restaurant_dict = {
            "public_id": restaurant.public_id,
            "name": restaurant.name,
            "description": restaurant.description,
            "phone_number": restaurant.phone_number,
            "address": restaurant.address,
            "is_open": restaurant.is_open,
            "image_url": restaurant.image_url,
            "created_at": restaurant.created_at,
            "average_rating": (
                round(float(average_rating), 1) if average_rating else None
            ),
            "total_ratings": total_ratings if total_ratings > 0 else 0,
        }
        restaurants.append(restaurant_dict)

    return restaurants


# ─── GET ONE RESTAURANT (CLIENT ONLY) ───────────────────


@router.get("/{public_id}", response_model=schemas.RestaurantResponse)
def get_restaurant(
    public_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_client),
):
    result = (
        db.execute(
            select(
                models.Restaurant,
                func.avg(models.Rating.rating).label("average_rating"),
                func.count(models.Rating.id).label("total_ratings"),
            )
            .outerjoin(
                models.Rating, models.Rating.restaurant_id == models.Restaurant.id
            )
            .where(models.Restaurant.public_id == public_id)
            .group_by(models.Restaurant.id)
        )
        .unique()
        .first()
    )

    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Restaurant not found"
        )

    restaurant, average_rating, total_ratings = result
    restaurant: models.Restaurant
    return {
        "public_id": restaurant.public_id,
        "name": restaurant.name,
        "description": restaurant.description,
        "phone_number": restaurant.phone_number,
        "address": restaurant.address,
        "is_open": restaurant.is_open,
        "image_url": restaurant.image_url,
        "created_at": restaurant.created_at,
        "average_rating": round(float(average_rating), 1) if average_rating else None,
        "total_ratings": total_ratings if total_ratings > 0 else 0,
    }


# ─── UPDATE RESTAURANT (OWNER ONLY) ─────────────────────


@router.put("/me", response_model=schemas.RestaurantResponse)
def update_restaurant(
    restaurant_data: schemas.RestaurantCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_owner),
):
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

    restaurant.name = restaurant_data.name
    restaurant.description = restaurant_data.description
    restaurant.phone_number = restaurant_data.phone_number
    restaurant.address = restaurant_data.address
    restaurant.is_open = restaurant_data.is_open

    db.commit()
    db.refresh(restaurant)

    return restaurant


# ─── DELETE RESTAURANT (OWNER ONLY) ─────────────────────


@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
def delete_restaurant(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_owner),
):
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

    db.delete(restaurant)
    db.commit()


@router.patch("/me", response_model=schemas.RestaurantResponse)
def patch_restaurant(
    restaurant_data: schemas.RestaurantUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_owner),
):
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

    # Only update fields that were actually sent
    update_data = restaurant_data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(restaurant, key, value)

    db.commit()
    db.refresh(restaurant)

    return restaurant


# ─── UPLOAD RESTAURANT IMAGE (OWNER ONLY) ────────────────


@router.post("/me/image", response_model=schemas.RestaurantResponse)
def upload_restaurant_image(
    file: UploadFile = File(...),
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

    # 2. Validate file type
    if file.content_type not in ["image/jpeg", "image/png", "image/webp"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only JPEG, PNG and WebP images are allowed",
        )

    # 3. Delete old image if exists
    if restaurant.image_url:
        public_id = cloudinary.utils.cloudinary_url(restaurant.image_url)[0]
        delete_image(public_id)

    # 4. Upload new image
    image_url = upload_image(file.file, folder="restaurants")

    # 5. Save image URL to database
    restaurant.image_url = image_url

    db.commit()
    db.refresh(restaurant)

    return restaurant
