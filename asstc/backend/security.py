import hashlib
import hmac
import html
import os
import re
import secrets
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

import jwt
from fastapi import Depends, HTTPException, Request, UploadFile, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from backend.config import settings
from backend.database import get_db
from backend.models import User

bearer_scheme = HTTPBearer(auto_error=False)


# --- Password Hashing (PBKDF2-HMAC-SHA256 with random salt) ---
def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 260000)
    return f"pbkdf2_sha256$260000${salt}${dk.hex()}"


def verify_password(plain_password: str, stored_hash: str) -> bool:
    try:
        algo, iterations_str, salt, hex_digest = stored_hash.split("$")
        if algo != "pbkdf2_sha256":
            return False
        dk = hashlib.pbkdf2_hmac(
            "sha256",
            plain_password.encode("utf-8"),
            salt.encode("utf-8"),
            int(iterations_str),
        )
        return hmac.compare_digest(dk.hex(), hex_digest)
    except Exception:
        return False


# --- Input Sanitization & URL Validation ---
def sanitize_text(value: str) -> str:
    if not value:
        return ""
    cleaned = re.sub(r"<script.*?>.*?</script>", "", value, flags=re.IGNORECASE | re.DOTALL)
    return html.escape(cleaned.strip(), quote=False)


def validate_external_url(url: Optional[str], required: bool = False) -> Optional[str]:
    if not url or not url.strip():
        if required:
            raise HTTPException(status_code=400, detail="URL is required.")
        return None
    cleaned = url.strip()
    parsed = urlparse(cleaned)
    if parsed.scheme not in ("https", "http") or not parsed.netloc:
        raise HTTPException(status_code=400, detail=f"Invalid URL '{cleaned}'. Only http:// and https:// URLs are allowed.")
    return cleaned


# --- JWT & Session Management ---
def create_access_token(user_id: int, role: str, expires_delta: Optional[timedelta] = None) -> str:
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    payload = {"sub": str(user_id), "role": role, "exp": expire}
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def generate_csrf_token(session_id: str) -> str:
    sig = hmac.new(settings.CSRF_SECRET.encode("utf-8"), session_id.encode("utf-8"), hashlib.sha256).hexdigest()
    return f"{session_id}.{sig}"


def verify_csrf_token(token: str) -> bool:
    if not token or "." not in token:
        return False
    session_id, sig = token.split(".", 1)
    expected = hmac.new(settings.CSRF_SECRET.encode("utf-8"), session_id.encode("utf-8"), hashlib.sha256).hexdigest()
    return hmac.compare_digest(sig, expected)


# --- Rate Limiting (Sliding Window In-Memory Store) ---
_rate_buckets: dict[str, list[float]] = {}


def enforce_rate_limit(request: Request, bucket_name: str, max_requests: int = 20, window_seconds: int = 60):
    client_ip = request.client.host if request.client else "127.0.0.1"
    key = f"{bucket_name}:{client_ip}"
    now = time.time()
    timestamps = [t for t in _rate_buckets.get(key, []) if now - t < window_seconds]
    if len(timestamps) >= max_requests:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded. Please wait before trying again.",
        )
    timestamps.append(now)
    _rate_buckets[key] = timestamps


# --- Safe Image Upload Validation (Never accept or execute binaries) ---
IMAGE_SIGNATURES = {
    b"\x89PNG\r\n\x1a\n": ".png",
    b"\xff\xd8\xff": ".jpg",
    b"RIFF": ".webp",
}


async def save_safe_image(upload: UploadFile) -> str:
    ext = Path(upload.filename or "").suffix.lower()
    if ext not in settings.ALLOWED_IMAGE_EXTS:
        raise HTTPException(
            status_code=400,
            detail="Unsupported file extension. Only PNG, JPG, and WEBP images are permitted. Executable files are strictly prohibited.",
        )
    if upload.content_type not in settings.ALLOWED_IMAGE_MIMES:
        raise HTTPException(status_code=400, detail="Invalid image MIME type.")

    content = await upload.read()
    if len(content) > settings.MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=400, detail="Image exceeds the 5 MB maximum size limit.")

    valid_magic = any(content.startswith(sig) for sig in IMAGE_SIGNATURES)
    if not valid_magic:
        raise HTTPException(status_code=400, detail="File header does not match a valid PNG, JPEG, or WEBP image.")

    safe_name = f"{secrets.token_hex(16)}{ext}"
    dest = settings.UPLOAD_DIR / safe_name
    dest.write_bytes(content)
    return f"/static/uploads/{safe_name}"


# --- Role-Based Authorization Dependencies ---
def get_current_user_optional(
    request: Request,
    creds: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> Optional[User]:
    token = None
    if creds and creds.credentials:
        token = creds.credentials
    elif "blockhub_token" in request.cookies:
        token = request.cookies.get("blockhub_token")

    if not token:
        return None
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id = int(payload.get("sub", 0))
    except Exception:
        return None

    user = db.query(User).filter(User.id == user_id).first()
    if not user or user.is_banned:
        return None
    return user


def get_current_user(user: Optional[User] = Depends(get_current_user_optional)) -> User:
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required.")
    return user


def require_developer(user: User = Depends(get_current_user)) -> User:
    if user.role not in ("developer", "admin"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Developer or Administrator role required.")
    return user


def require_admin(user: User = Depends(get_current_user)) -> User:
    if user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Administrator privileges required.")
    return user
