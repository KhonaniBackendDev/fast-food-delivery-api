from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    database_hostname: str
    database_port: int
    database_password: str
    database_name: str
    database_username: str
    secret_key: str
    algorithm: str
    access_token_expire_minutes: int
    refresh_token_expire_days: int

    resend_api_key: str
    resend_from_email: str
    frontend_url: str

    twilio_account_sid: str
    twilio_auth_token: str
    twilio_phone_number: str

    cloudinary_cloud_name: str
    cloudinary_api_key: str
    cloudinary_api_secret: str

    max_reset_attempts: int = 3
    reset_attempt_window_hours: int = 24
    reset_token_expire_minutes: int = 15

    stripe_secret_key: str
    stripe_webhook_secret: str
    stripe_publishable_key: str

    openai_api_key: Optional[str] = None
    base_url: str = "http://localhost:8000"

    env: str

    class Config:
        env_file = ".env"

    @property
    def database_url(self):
        return f"postgresql://{self.database_username}:{self.database_password}@{self.database_hostname}:{self.database_port}/{self.database_name}"


settings = Settings()
