import app.utils.cloudinary as cloudinary
import cloudinary.uploader
from app.config import settings

cloudinary.config(
    cloud_name=settings.cloudinary_cloud_name,
    api_key=settings.cloudinary_api_key,
    api_secret=settings.cloudinary_api_secret,
)


def upload_image(file, folder: str) -> str:
    result = cloudinary.uploader.upload(file, folder=folder, resource_type="image")
    return result["secure_url"]


def delete_image(public_id: str) -> None:
    cloudinary.uploader.destroy(public_id)
