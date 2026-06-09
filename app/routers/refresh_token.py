from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import select

from .. import schemas
from .. import models
from ..database import get_db
from .auth import create_access_token
from datetime import datetime, timezone

router = APIRouter(prefix="/refresh", tags=["Token Refresh"])


@router.post("/", response_model=schemas.Token)
def refresh_access_token(refresh_token: str, db: Session = Depends(get_db)):
    # 1. Find the refresh token in database
    token_record = db.execute(
        select(models.RefreshToken).where(models.RefreshToken.token == refresh_token)
    ).scalar_one_or_none()

    # 2. Check if it exists
    if not token_record:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token"
        )

    # 3. Check if it has expired
    if token_record.expires_at < datetime.now(timezone.utc):
        db.delete(token_record)
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token has expired. Please log in again",
        )

    # 4. Generate new access token
    access_token = create_access_token(data={"user_id": token_record.user_id})

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
    }
