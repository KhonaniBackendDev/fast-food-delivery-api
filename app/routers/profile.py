from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.orm import Session
from sqlalchemy import select, delete

from .. import schemas
from .. import models
from ..database import get_db
from ..utils.oauth2 import get_current_user
from ..utils.hashing import hash_password, verify_hashed_password
from ..utils.cloudinary import upload_image, delete_image
import cloudinary.utils

router = APIRouter(prefix="/profile", tags=["Profile"])


# ─── GET MY PROFILE (EVERYONE) ───────────────────────────


@router.get("/me", response_model=schemas.UserResponse)
def get_my_profile(
    db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)
):
    return current_user


# ─── UPDATE MY PROFILE (EVERYONE) ────────────────────────


@router.put("/me", response_model=schemas.UserResponse)
def update_my_profile(
    profile_data: schemas.ProfileUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    # Check if new phone number is already taken by someone else
    if profile_data.phone_number:
        existing_phone = db.execute(
            select(models.User).where(
                models.User.phone_number == profile_data.phone_number,
                models.User.id != current_user.id,
            )
        ).scalar_one_or_none()

        if existing_phone:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Phone number already in use",
            )
    # Check if new email is already taken by someone else
    if profile_data.email:
        existing_email = db.execute(
            select(models.User).where(
                models.User.email == profile_data.email,
                models.User.id != current_user.id,
            )
        ).scalar_one_or_none()

        if existing_email:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, detail="Email already in use"
            )

    current_user.name = profile_data.name or current_user.name
    current_user.phone_number = profile_data.phone_number or current_user.phone_number
    current_user.email = profile_data.email or current_user.email

    db.commit()
    db.refresh(current_user)

    return current_user


# ─── PATCH MY PROFILE (EVERYONE) ─────────────────────────


@router.patch("/me", response_model=schemas.UserResponse)
def patch_my_profile(
    profile_data: schemas.ProfileUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    # Check if new phone number is already taken by someone else
    if profile_data.phone_number:
        existing_phone = db.execute(
            select(models.User).where(
                models.User.phone_number == profile_data.phone_number,
                models.User.id != current_user.id,
            )
        ).scalar_one_or_none()

        if existing_phone:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Phone number already in use",
            )

    # Check if new email is already taken by someone else
    if profile_data.email:
        existing_email = db.execute(
            select(models.User).where(
                models.User.email == profile_data.email,
                models.User.id != current_user.id,
            )
        ).scalar_one_or_none()

        if existing_email:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, detail="Email already in use"
            )

    update_data = profile_data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(current_user, key, value)

    db.commit()
    db.refresh(current_user)

    return current_user


# ─── CHANGE PASSWORD (EVERYONE) ──────────────────────────


@router.post("/me/change-password", status_code=status.HTTP_204_NO_CONTENT)
def change_password(
    password_data: schemas.ChangePassword,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    # 1. Verify current password is correct
    if not verify_hashed_password(
        password_data.current_password, current_user.password
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Current password is incorrect",
        )

    # 2. Make sure new password and confirm password match
    if password_data.new_password != password_data.confirm_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password and confirm password do not match",
        )

    # 3. Make sure new password is different from current password
    if password_data.current_password == password_data.new_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password must be different from current password",
        )

    # 4. Hash and save new password
    current_user.password = hash_password(password_data.new_password)

    # 5. Delete all refresh tokens → force login again on all devices
    db.execute(
        delete(models.RefreshToken).where(
            models.RefreshToken.user_id == current_user.id
        )
    )

    db.commit()


# ─── UPLOAD PROFILE IMAGE (EVERYONE) ─────────────────────


@router.post("/me/image", response_model=schemas.UserResponse)
def upload_profile_image(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    # 1. Validate file type
    if file.content_type not in ["image/jpeg", "image/png", "image/webp"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only JPEG, PNG and WebP images are allowed",
        )

    # 2. Upload image
    image_url = upload_image(file.file, folder="profiles")

    # 3. Save to database
    current_user.image_url = image_url

    db.commit()
    db.refresh(current_user)

    return current_user
