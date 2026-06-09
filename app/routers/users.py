from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import select

from .. import schemas
from .. import models
from ..database import get_db
from ..utils.hashing import hash_password
from ..utils.oauth2 import create_access_token
import secrets
import random
from ..utils.email import send_verification_email
from ..utils.sms import send_phone_verification_sms
from ..enumz import TokenType
from ..config import settings
from datetime import datetime, timezone, timedelta

router = APIRouter(prefix="/users", tags=["Users"])


@router.post(
    "/register",
    response_model=schemas.UserRegisterResponse,
    status_code=status.HTTP_201_CREATED,
)
def register_user(user_data: schemas.UserCreate, db: Session = Depends(get_db)):
    # 1. Check if email already exists
    existing_email = db.execute(
        select(models.User).where(models.User.email == user_data.email)
    ).scalar_one_or_none()

    if existing_email:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Email already registered"
        )

    # 2. Check if phone number already exists
    existing_phone = db.execute(
        select(models.User).where(models.User.phone_number == user_data.phone_number)
    ).scalar_one_or_none()

    if existing_phone:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Phone number already registered",
        )

    # 3. Hash the password
    hashed_password = hash_password(user_data.password)

    # 4. Save the user
    new_user = models.User(
        name=user_data.name,
        email=user_data.email,
        phone_number=user_data.phone_number,
        password=hashed_password,
        role=user_data.role,
    )

    db.add(new_user)
    db.flush()

    # Access token
    access_token = create_access_token(data={"user_id": str(new_user.public_id)})

    # Create Refresh token
    refresh_token_value = secrets.token_hex(32)
    refresh_token_expires = datetime.now(timezone.utc) + timedelta(
        days=settings.refresh_token_expire_days
    )

    new_refresh_token = models.RefreshToken(
        user_id=new_user.id, token=refresh_token_value, expires_at=refresh_token_expires
    )
    db.add(new_refresh_token)

    # 7. Generate email verification token
    email_verification_token = secrets.token_urlsafe(32)
    email_token_expires = datetime.now(timezone.utc) + timedelta(hours=24)

    new_email_token = models.VerificationToken(
        user_id=new_user.id,
        token=email_verification_token,
        type=TokenType.email_verification,
        expires_at=email_token_expires,
    )
    db.add(new_email_token)

    # 8. Generate phone verification code
    phone_code = str(random.randint(100000, 999999))  # 6 digit code
    phone_code_expires = datetime.now(timezone.utc) + timedelta(minutes=20)

    new_phone_token = models.VerificationToken(
        user_id=new_user.id,
        token=phone_code,
        type=TokenType.phone_verification,
        expires_at=phone_code_expires,
    )
    db.add(new_phone_token)
    db.commit()
    db.refresh(new_user)

    # 9. Send verification email
    send_verification_email(
        to=new_user.email, name=new_user.name, token=email_verification_token
    )

    # 10. Send phone verification SMS
    send_phone_verification_sms(to=new_user.phone_number, code=phone_code)

    return {
        "user": new_user,
        "access_token": access_token,
        "refresh_token": refresh_token_value,
        "token_type": "bearer",
    }
