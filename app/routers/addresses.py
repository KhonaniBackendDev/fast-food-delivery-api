from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import select

from .. import schemas
from .. import models
from ..database import get_db
from ..utils.oauth2 import get_current_client
from uuid import UUID

router = APIRouter(prefix="/addresses", tags=["Addresses"])


# ─── CREATE ADDRESS (CLIENT ONLY) ────────────────────────


@router.post(
    "/", response_model=schemas.AddressResponse, status_code=status.HTTP_201_CREATED
)
def create_address(
    address_data: schemas.AddressCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_client),
):
    # 1. If this address is set as default
    # remove default from all other addresses first
    if address_data.is_default:
        existing_addresses = (
            db.execute(
                select(models.Address).where(models.Address.user_id == current_user.id)
            )
            .scalars()
            .all()
        )

        for existing_address in existing_addresses:
            existing_address.is_default = False

    # 2. Create the new address
    new_address = models.Address(
        user_id=current_user.id,
        street=address_data.street,
        city=address_data.city,
        state=address_data.state,
        province=address_data.province,
        country=address_data.country,
        postal_code=address_data.postal_code,
        is_default=address_data.is_default,
    )

    db.add(new_address)
    db.commit()
    db.refresh(new_address)

    return new_address


# ─── GET ALL MY ADDRESSES (CLIENT ONLY) ──────────────────


@router.get("/", response_model=list[schemas.AddressResponse])
def get_my_addresses(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_client),
):
    addresses = (
        db.execute(
            select(models.Address)
            .where(models.Address.user_id == current_user.id)
            .order_by(models.Address.is_default.desc())
        )
        .scalars()
        .all()
    )

    return addresses


# ─── GET ONE ADDRESS (CLIENT ONLY) ───────────────────────


@router.get("/{address_public_id}", response_model=schemas.AddressResponse)
def get_one_address(
    address_public_id: UUID,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_client),
):
    address = db.execute(
        select(models.Address).where(
            models.Address.public_id == address_public_id,
            models.Address.user_id == current_user.id,
        )
    ).scalar_one_or_none()

    if not address:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Address not found"
        )

    return address


# ─── UPDATE ADDRESS (CLIENT ONLY) ────────────────────────


@router.put("/{address_public_id}", response_model=schemas.AddressResponse)
def update_address(
    address_public_id: UUID,
    address_data: schemas.AddressCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_client),
):
    address = db.execute(
        select(models.Address).where(
            models.Address.public_id == address_public_id,
            models.Address.user_id == current_user.id,
        )
    ).scalar_one_or_none()

    if not address:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Address not found"
        )

    # If setting this as default, remove default from others first
    if address_data.is_default:
        existing_addresses = (
            db.execute(
                select(models.Address).where(
                    models.Address.user_id == current_user.id,
                    models.Address.public_id != address_public_id,
                )
            )
            .scalars()
            .all()
        )

        for existing_address in existing_addresses:
            existing_address.is_default = False

    address.street = address_data.street
    address.city = address_data.city
    address.state = address_data.state
    address.province = address_data.province
    address.country = address_data.country
    address.postal_code = address_data.postal_code
    address.is_default = address_data.is_default

    db.commit()
    db.refresh(address)

    return address


# ─── PATCH ADDRESS (CLIENT ONLY) ─────────────────────────


@router.patch("/{address_public_id}", response_model=schemas.AddressResponse)
def patch_address(
    address_public_id: UUID,
    address_data: schemas.AddressUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_client),
):
    address = db.execute(
        select(models.Address).where(
            models.Address.public_id == address_public_id,
            models.Address.user_id == current_user.id,
        )
    ).scalar_one_or_none()

    if not address:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Address not found"
        )

    # If setting this as default, remove default from others first
    if address_data.is_default:
        existing_addresses = (
            db.execute(
                select(models.Address).where(
                    models.Address.user_id == current_user.id,
                    models.Address.public_id != address_public_id,
                )
            )
            .scalars()
            .all()
        )

        for existing_address in existing_addresses:
            existing_address.is_default = False

    update_data = address_data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(address, key, value)

    db.commit()
    db.refresh(address)

    return address


# ─── SET DEFAULT ADDRESS (CLIENT ONLY) ───────────────────


@router.patch(
    "/{address_public_id}/set-default", response_model=schemas.AddressResponse
)
def set_default_address(
    address_public_id: UUID,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_client),
):
    # 1. Remove default from all addresses
    existing_addresses = (
        db.execute(
            select(models.Address).where(models.Address.user_id == current_user.id)
        )
        .scalars()
        .all()
    )

    for existing_address in existing_addresses:
        existing_address.is_default = False

    # 2. Set this one as default
    address = db.execute(
        select(models.Address).where(
            models.Address.public_id == address_public_id,
            models.Address.user_id == current_user.id,
        )
    ).scalar_one_or_none()

    if not address:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Address not found"
        )

    address.is_default = True

    db.commit()
    db.refresh(address)

    return address


# ─── DELETE ADDRESS (CLIENT ONLY) ────────────────────────


@router.delete("/{address_public_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_address(
    address_public_id: UUID,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_client),
):
    address = db.execute(
        select(models.Address).where(
            models.Address.public_id == address_public_id,
            models.Address.user_id == current_user.id,
        )
    ).scalar_one_or_none()

    if not address:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Address not found"
        )

    db.delete(address)
    db.commit()
