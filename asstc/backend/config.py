import os
import secrets
from pathlib import Path


class Settings:
    APP_NAME: str = os.getenv("APP_NAME", "BLOCKHUB")
    TAGLINE: str = "DISCOVER. PUBLISH. PLAY."
    APP_ENV: str = os.getenv("APP_ENV", "development")
    APP_URL: str = os.getenv("APP_URL", "http://127.0.0.1:8000")

    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./blockhub.db")

    SECRET_KEY: str = os.getenv("SECRET_KEY", secrets.token_urlsafe(48))
    CSRF_SECRET: str = os.getenv("CSRF_SECRET", secrets.token_urlsafe(32))
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "1440"))
    COOKIE_SECURE: bool = os.getenv("COOKIE_SECURE", "false").lower() == "true" or APP_ENV == "production"

    # Initial Admin Bootstrap (never hardcoded; read from server-side environment)
    FIRST_ADMIN_EMAIL: str = os.getenv("FIRST_ADMIN_EMAIL", "krish137u@gmail.com")
    FIRST_ADMIN_USERNAME: str = os.getenv("FIRST_ADMIN_USERNAME", "krish_admin")

    UPLOAD_DIR: Path = Path(os.getenv("UPLOAD_DIR", "frontend/static/uploads"))
    MAX_UPLOAD_BYTES: int = int(os.getenv("MAX_UPLOAD_SIZE_MB", "5")) * 1024 * 1024
    ALLOWED_IMAGE_MIMES: set[str] = {"image/png", "image/jpeg", "image/webp"}
    ALLOWED_IMAGE_EXTS: set[str] = {".png", ".jpg", ".jpeg", ".webp"}

    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    LOG_FILE: Path = Path(os.getenv("LOG_FILE", "logs/blockhub.log"))


settings = Settings()
settings.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
settings.LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
