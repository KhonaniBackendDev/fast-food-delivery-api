from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.orm import Session
from sqlalchemy import select

from .. import schemas
from .. import models
from ..database import get_db
from ..utils.oauth2 import get_current_owner, get_current_client
from uuid import UUID
from ..utils.cloudinary import upload_image, delete_image
import cloudinary.utils

router = APIRouter(prefix="/foods", tags=["Foods"])


# ─── CREATE FOOD (OWNER ONLY) ────────────────────────────


@router.post(
    "/", response_model=schemas.FoodResponse, status_code=status.HTTP_201_CREATED
)
def create_food(
    food_data: schemas.FoodCreate,
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

    # 2. Create food
    new_food = models.Food(
        restaurant_id=restaurant.id,
        name=food_data.name,
        description=food_data.description,
        price=food_data.price,
        is_available=food_data.is_available,
        image_url=food_data.image_url,
    )

    db.add(new_food)
    db.commit()
    db.refresh(new_food)

    return new_food


# ─── GET MY RESTAURANT'S FOODS (OWNER ONLY) ──────────────


@router.get("/me", response_model=list[schemas.FoodResponse])
def get_my_foods(
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

    # 2. Get all foods for that restaurant
    foods = (
        db.execute(
            select(models.Food).where(models.Food.restaurant_id == restaurant.id)
        )
        .scalars()
        .all()
    )

    if not foods:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="You're restaurant is currently empty",
        )

    return foods


# ─── GET ALL FOODS FROM A RESTAURANT (CLIENT ONLY) ───────


@router.get("/{restaurant_public_id}", response_model=list[schemas.FoodResponse])
def get_restaurant_foods(
    restaurant_public_id: UUID,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_client),
):
    # 1. Find the restaurant
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

    # 2. Get all available foods for that restaurant
    foods = (
        db.execute(
            select(models.Food).where(
                models.Food.restaurant_id == restaurant.id,
                models.Food.is_available == True,
            )
        )
        .scalars()
        .all()
    )

    return foods


# ─── GET ONE FOOD ITEM (CLIENT ONLY) ─────────────────────


@router.get(
    "/{restaurant_public_id}/{food_public_id}", response_model=schemas.FoodResponse
)
def get_one_food(
    restaurant_public_id: UUID,
    food_public_id: UUID,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_client),
):
    # 1. Find the restaurant
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

    # 2. Find the food inside that restaurant
    food = db.execute(
        select(models.Food).where(
            models.Food.public_id == food_public_id,
            models.Food.restaurant_id == restaurant.id,
        )
    ).scalar_one_or_none()

    if not food:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Food item not found"
        )

    return food


# ─── UPDATE FOOD (OWNER ONLY) ────────────────────────────


@router.put("/{food_public_id}", response_model=schemas.FoodResponse)
def update_food(
    food_public_id: UUID,
    food_data: schemas.FoodCreate,
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

    # 2. Find the food and make sure it belongs to their restaurant
    food = db.execute(
        select(models.Food).where(
            models.Food.public_id == food_public_id,
            models.Food.restaurant_id == restaurant.id,
        )
    ).scalar_one_or_none()

    if not food:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Food item not found"
        )

    food.name = food_data.name
    food.description = food_data.description
    food.price = food_data.price
    food.is_available = food_data.is_available
    food.image_url = food_data.image_url

    db.commit()
    db.refresh(food)

    return food


# ─── PATCH FOOD (OWNER ONLY) ─────────────────────────────


@router.patch("/{food_public_id}", response_model=schemas.FoodResponse)
def patch_food(
    food_public_id: UUID,
    food_data: schemas.FoodUpdate,
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

    # 2. Find the food
    food = db.execute(
        select(models.Food).where(
            models.Food.public_id == food_public_id,
            models.Food.restaurant_id == restaurant.id,
        )
    ).scalar_one_or_none()

    if not food:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Food item not found"
        )

    update_data = food_data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(food, key, value)

    db.commit()
    db.refresh(food)

    return food


# ─── DELETE FOOD (OWNER ONLY) ────────────────────────────


@router.delete("/{food_public_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_food(
    food_public_id: UUID,
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

    # 2. Find the food
    food = db.execute(
        select(models.Food).where(
            models.Food.public_id == food_public_id,
            models.Food.restaurant_id == restaurant.id,
        )
    ).scalar_one_or_none()

    if not food:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Food item not found"
        )

    db.delete(food)
    db.commit()


# ─── UPLOAD FOOD IMAGE (OWNER ONLY) ──────────────────────


@router.post("/{food_public_id}/image", response_model=schemas.FoodResponse)
def upload_food_image(
    food_public_id: UUID,
    file: UploadFile = File(...),
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

    # 2. Get the food and make sure it belongs to their restaurant
    food = db.execute(
        select(models.Food).where(
            models.Food.public_id == food_public_id,
            models.Food.restaurant_id == restaurant.id,
        )
    ).scalar_one_or_none()

    if not food:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Food item not found"
        )

    # 3. Validate file type
    if file.content_type not in ["image/jpeg", "image/png", "image/webp"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only JPEG, PNG and WebP images are allowed",
        )

    # 4. Delete old image if exists
    if food.image_url:
        public_id = cloudinary.utils.cloudinary_url(food.image_url)[0]
        delete_image(public_id)

    # 5. Upload new image
    image_url = upload_image(file.file, folder="foods")

    # 6. Save image URL to database
    food.image_url = image_url

    db.commit()
    db.refresh(food)

    return food
