from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import select, delete
from datetime import datetime, timezone, timedelta
from .. import models, schemas
from ..database import get_db
from ..utils.oauth2 import get_current_user
from ..utils.email import (
    send_verification_email,
    send_password_reset_email,
    send_welcome_email,
    send_password_changed_email,
)
from ..utils.sms import send_phone_verification_sms
from ..utils.hashing import hash_password
from ..enumz import TokenType
from ..config import settings
import secrets
import random
import resend

router = APIRouter(tags=["Verification"])


# ─── VERIFY PHONE ─────────────────────────────────────────


@router.post("/verify-phone")
def verify_phone(
    verification_data: schemas.VerifyPhone,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    phone_token = db.execute(
        select(models.VerificationToken).where(
            models.VerificationToken.user_id == current_user.id,
            models.VerificationToken.token == verification_data.code,
            models.VerificationToken.type == TokenType.phone_verification,
            models.VerificationToken.is_used == False,
        )
    ).scalar_one_or_none()

    if not phone_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid verification code"
        )

    if phone_token.expires_at.replace(tzinfo=timezone.utc) < datetime.now(timezone.utc):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Verification code has expired. Please request a new one",
        )

    current_user.is_phone_verified = True
    phone_token.is_used = True

    if current_user.is_email_verified:
        current_user.is_verified = True
        db.commit()
        send_welcome_email(to=current_user.email, name=current_user.name)
    else:
        db.commit()

    return {"message": "Phone number verified successfully"}


# ─── VERIFY EMAIL ─────────────────────────────────────────


@router.get("/verify-email")
def verify_email(token: str, db: Session = Depends(get_db)):
    email_token = db.execute(
        select(models.VerificationToken).where(
            models.VerificationToken.token == token,
            models.VerificationToken.type == TokenType.email_verification,
            models.VerificationToken.is_used == False,
        )
    ).scalar_one_or_none()

    if not email_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid verification token"
        )

    if email_token.expires_at.replace(tzinfo=timezone.utc) < datetime.now(timezone.utc):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Verification token has expired. Please request a new one",
        )

    user = db.execute(
        select(models.User).where(models.User.id == email_token.user_id)
    ).scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    user.is_email_verified = True
    email_token.is_used = True

    if user.is_phone_verified:
        user.is_verified = True
        db.commit()
        send_welcome_email(to=user.email, name=user.name)
    else:
        db.commit()

    return {"message": "Email verified successfully"}


# ─── RESEND PHONE CODE ────────────────────────────────────


@router.post("/resend-phone-code")
def resend_phone_code(
    db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)
):
    if current_user.is_phone_verified:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Phone number is already verified",
        )

    db.execute(
        delete(models.VerificationToken).where(
            models.VerificationToken.user_id == current_user.id,
            models.VerificationToken.type == TokenType.phone_verification,
        )
    )

    phone_code = str(random.randint(100000, 999999))
    phone_code_expires = datetime.now(timezone.utc) + timedelta(minutes=10)

    new_phone_token = models.VerificationToken(
        user_id=current_user.id,
        token=phone_code,
        type=TokenType.phone_verification,
        expires_at=phone_code_expires,
    )

    db.add(new_phone_token)
    db.commit()

    send_phone_verification_sms(to=current_user.phone_number, code=phone_code)

    return {"message": "Verification code sent. Please check your phone"}


# ─── RESEND VERIFICATION EMAIL ────────────────────────────


@router.post("/resend-verification-email")
def resend_verification_email(
    db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)
):
    if current_user.is_email_verified:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Email is already verified"
        )

    db.execute(
        delete(models.VerificationToken).where(
            models.VerificationToken.user_id == current_user.id,
            models.VerificationToken.type == TokenType.email_verification,
        )
    )

    email_token = secrets.token_urlsafe(32)
    email_token_expires = datetime.now(timezone.utc) + timedelta(hours=24)

    new_email_token = models.VerificationToken(
        user_id=current_user.id,
        token=email_token,
        type=TokenType.email_verification,
        expires_at=email_token_expires,
    )

    db.add(new_email_token)
    db.commit()

    send_verification_email(
        to=current_user.email, name=current_user.name, token=email_token
    )

    return {"message": "Verification email sent. Please check your inbox"}


# ─── FORGOT PASSWORD ──────────────────────────────────────


@router.post("/forgot-password")
def forgot_password(email_data: schemas.ForgotPassword, db: Session = Depends(get_db)):
    user = db.execute(
        select(models.User).where(models.User.email == email_data.email)
    ).scalar_one_or_none()

    if not user:
        return {
            "message": "If this email is registered you will receive a reset link shortly"
        }

    recent_attempts = (
        db.execute(
            select(models.VerificationToken).where(
                models.VerificationToken.user_id == user.id,
                models.VerificationToken.type == TokenType.password_reset,
                models.VerificationToken.created_at
                >= datetime.now(timezone.utc)
                - timedelta(hours=settings.reset_attempt_window_hours),
            )
        )
        .scalars()
        .all()
    )

    if len(recent_attempts) >= settings.max_reset_attempts:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Too many password reset attempts. Please try again in {settings.reset_attempt_window_hours} hours",
        )

    reset_token = secrets.token_urlsafe(32)
    token_expires = datetime.now(timezone.utc) + timedelta(
        minutes=settings.reset_token_expire_minutes
    )

    new_token = models.VerificationToken(
        user_id=user.id,
        token=reset_token,
        type=TokenType.password_reset,
        expires_at=token_expires,
    )

    db.add(new_token)
    db.commit()

    send_password_reset_email(to=user.email, name=user.name, token=reset_token)

    return {
        "message": "If this email is registered you will receive a reset link shortly"
    }


# ─── RESET PASSWORD ───────────────────────────────────────


@router.post("/reset-password")
def reset_password(reset_data: schemas.ResetPassword, db: Session = Depends(get_db)):
    reset_token = db.execute(
        select(models.VerificationToken).where(
            models.VerificationToken.token == reset_data.token,
            models.VerificationToken.type == TokenType.password_reset,
            models.VerificationToken.is_used == False,
        )
    ).scalar_one_or_none()

    if not reset_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid reset token"
        )

    if reset_token.expires_at.replace(tzinfo=timezone.utc) < datetime.now(timezone.utc):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Reset token has expired. Please request a new one",
        )

    user = db.execute(
        select(models.User).where(models.User.id == reset_token.user_id)
    ).scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    if reset_data.new_password != reset_data.confirm_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Passwords do not match"
        )

    user.password = hash_password(reset_data.new_password)
    reset_token.is_used = True

    db.execute(
        delete(models.RefreshToken).where(models.RefreshToken.user_id == user.id)
    )

    db.commit()

    send_password_changed_email(to=user.email, name=user.name)

    return {
        "message": "Password reset successfully. Please log in with your new password"
    }
    
    
@router.post("/demo/verify/{user_public_id}")
def demo_verify_user(
    user_public_id: str,
    db: Session = Depends(get_db)
):
    # Block this endpoint if environment is production
    if settings.env not in ["development", "demo"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This endpoint is not available in production"
        )

    user = db.execute(
        select(models.User).where(
            models.User.public_id == user_public_id
        )
    ).scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    user.is_email_verified = True
    user.is_phone_verified = True
    user.is_verified = True

    db.commit()

    return {"message": "User verified successfully for demo purposes"}    


# # ─── EMERGENCY LOCK ───────────────────────────────────────


# @router.post("/emergency-lock")
# def emergency_lock(email_data: schemas.ForgotPassword, db: Session = Depends(get_db)):
#     user = db.execute(
#         select(models.User).where(models.User.email == email_data.email)
#     ).scalar_one_or_none()

#     if not user:
#         return {"message": "If this email exists we have locked the account"}

#     user.locked_until = datetime.now(timezone.utc) + timedelta(days=30)

#     db.execute(
#         delete(models.RefreshToken).where(models.RefreshToken.user_id == user.id)
#     )

#     db.commit()

#     resend.Emails.send(
#         {
#             "from": settings.resend_from_email,
#             "to": user.email,
#             "subject": "Your account has been locked",
#             "html": f"""
#             <h2>Hi {user.name},</h2>
#             <p>Your account has been locked for 30 days as requested.</p>
#             <p>To recover your account please reset your password using the forgot password option.</p>
#         """,
#         }
#     )

#     return {"message": "If this email exists we have locked the account"}
