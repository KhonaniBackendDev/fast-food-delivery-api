from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from sqlalchemy import select, delete
from datetime import datetime, timezone, timedelta

from .. import schemas
from .. import models
from ..database import get_db
from ..utils.hashing import verify_hashed_password
from ..utils.oauth2 import create_access_token, get_current_user
import secrets
from ..config import settings

router = APIRouter(prefix="/auth", tags=["Authentication"])

MAX_ATTEMPTS = 3
LOCK_TIME = timedelta(minutes=30)


@router.post("/login", response_model=schemas.Token)
def login_user(
    user_credentials: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):

    # Get user
    user = db.execute(
        select(models.User).where(models.User.email == user_credentials.username)
    ).scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Incorrect user credentials"
        )

    if user.locked_until and user.locked_until > datetime.now(timezone.utc):
        remaining = user.locked_until - datetime.now(timezone.utc)
        minutes_remaining = int(remaining.total_seconds() / 60)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Account locked. Try again in {minutes_remaining} minutes",
        )
    # Wrong password
    if not verify_hashed_password(user_credentials.password, user.password):
        user.failed_attempts += 1

        if user.failed_attempts >= MAX_ATTEMPTS:
            user.locked_until = datetime.now(timezone.utc) + LOCK_TIME
            user.failed_attempts = 0  # reset after lock

        db.commit()

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Invalid credentials"
        )

    # Correct password
    user.failed_attempts = 0
    user.locked_until = None
    db.commit()

    access_token = create_access_token(data={"user_id": str(user.public_id)})

    # Create refresh token
    refresh_token_value = secrets.token_hex(32)
    refresh_token_expires = datetime.now(timezone.utc) + timedelta(
        days=settings.refresh_token_expire_days
    )

    # Delete any existing refresh tokens for this user
    db.execute(
        delete(models.RefreshToken).where(models.RefreshToken.user_id == user.id)
    )

    # Save new refresh token to database
    new_refresh_token = models.RefreshToken(
        user_id=user.id, token=refresh_token_value, expires_at=refresh_token_expires
    )
    db.add(new_refresh_token)
    db.commit()

    return {
        "access_token": access_token,
        "refresh_token": refresh_token_value,
        "token_type": "bearer",
    }


# ─── LOGOUT ──────────────────────────────────────────────


@router.post("/logout", status_code=status.HTTP_200_OK)
def logout(
    logout_data: schemas.LogoutRequest, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)
):
    # Delete the user's refresh token from the database
    db.execute(
        delete(models.RefreshToken).where(
            models.RefreshToken.token == logout_data.refresh_token,
            models.RefreshToken.user_id == current_user.id,
        )
    )

    db.commit()

    return {"message": "Logged out successfully"}


    # db.execute(
    #     delete(models.RefreshToken).where(
    #         models.RefreshToken.user_id == current_user.id
    #     )
    # )
    # db.commit()
