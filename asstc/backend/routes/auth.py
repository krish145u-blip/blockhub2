import secrets
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy import or_
from sqlalchemy.orm import Session

from backend.config import settings
from backend.database import get_db
from backend.models import DeveloperProfile, Notification, User, UserProfile
from backend.schemas import LoginRequest, ProfileUpdateRequest, RegisterRequest
from backend.security import (
    create_access_token,
    enforce_rate_limit,
    generate_csrf_token,
    get_current_user,
    get_current_user_optional,
    hash_password,
    sanitize_text,
    validate_external_url,
    verify_password,
)

router = APIRouter(prefix="/api/auth", tags=["Authentication"])


@router.get("/session")
def get_session_status(user: User | None = Depends(get_current_user_optional)):
    # Section 25: Visitors without a valid authenticated session always receive Guest status
    if not user:
        return {"authenticated": False, "role": "guest", "user": None}
    return {
        "authenticated": True,
        "role": user.role,
        "user": {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "role": user.role,
            "is_email_verified": user.is_email_verified,
        },
    }


@router.get("/check-username")
def check_username(username: str, db: Session = Depends(get_db)):
    exists = db.query(User).filter(User.username.ilike(username.strip())).first() is not None
    return {"username": username, "available": not exists}


@router.post("/register", status_code=201)
def register_user(payload: RegisterRequest, request: Request, db: Session = Depends(get_db)):
    enforce_rate_limit(request, "auth_register", max_requests=10, window_seconds=60)
    if not payload.accept_terms:
        raise HTTPException(status_code=400, detail="You must accept the Terms and Conditions.")

    # Section 25: Public registration never assigns Developer or Administrator privileges automatically
    if payload.role != "user":
        raise HTTPException(status_code=403, detail="Public registration cannot assign developer or administrator privileges.")

    existing = db.query(User).filter(
        or_(User.username.ilike(payload.username), User.email.ilike(payload.email))
    ).first()
    if existing:
        raise HTTPException(status_code=409, detail="Username or email is already registered.")

    verify_token = secrets.token_urlsafe(32)
    user = User(
        username=payload.username.strip(),
        email=payload.email.lower().strip(),
        password_hash=hash_password(payload.password),
        role="user",
        is_email_verified=False,
        verification_token=verify_token,
    )
    db.add(user)
    db.flush()

    db.add(UserProfile(user_id=user.id, bio="Minecraft community member on BLOCKHUB."))
    db.add(
        Notification(
            user_id=user.id,
            title="Welcome to BLOCKHUB!",
            message="Please verify your email address and log in to access your personal dashboard.",
            notif_type="system",
        )
    )
    db.commit()
    db.refresh(user)

    # Section 25: Require explicit login after registration
    return {
        "message": "Registration complete. Please log in with your credentials.",
        "require_login": True,
        "user": {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "role": user.role,
            "is_email_verified": user.is_email_verified,
        },
    }


@router.post("/login")
def login_user(payload: LoginRequest, request: Request, response: Response, db: Session = Depends(get_db)):
    enforce_rate_limit(request, "auth_login", max_requests=15, window_seconds=60)
    ident = payload.identifier.strip()
    user = db.query(User).filter(or_(User.username.ilike(ident), User.email.ilike(ident))).first()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid username/email or password.")
    if user.is_banned:
        raise HTTPException(status_code=403, detail="This account has been suspended by moderation.")

    token = create_access_token(user.id, user.role)
    csrf = generate_csrf_token(str(user.id))

    # Section 25: Remember Me is disabled by default; only set persistent max_age when explicitly requested
    cookie_kwargs = {
        "key": "blockhub_token",
        "value": token,
        "httponly": True,
        "secure": settings.COOKIE_SECURE,
        "samesite": "lax",
    }
    if payload.remember_me:
        cookie_kwargs["max_age"] = 86400 * 14

    response.set_cookie(**cookie_kwargs)
    return {
        "message": "Logged in.",
        "access_token": token,
        "csrf_token": csrf,
        "remember_me": payload.remember_me,
        "user": {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "role": user.role,
            "is_email_verified": user.is_email_verified,
        },
    }


@router.post("/logout")
def logout_user(response: Response):
    response.delete_cookie("blockhub_token", httponly=True, samesite="lax", secure=settings.COOKIE_SECURE)
    return {"message": "Logged out. Returned to Guest status.", "role": "guest", "authenticated": False}


@router.post("/verify-email")
def verify_email(token: str, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.verification_token == token).first()
    if not user:
        raise HTTPException(status_code=400, detail="Invalid or expired email verification token.")
    user.is_email_verified = True
    user.verification_token = None
    db.add(
        Notification(
            user_id=user.id,
            title="Account Verified",
            message="Your email address has been verified.",
            notif_type="verification",
        )
    )
    db.commit()
    return {"message": "Email verified."}


@router.post("/forgot-password")
def forgot_password(email: str, request: Request, db: Session = Depends(get_db)):
    enforce_rate_limit(request, "auth_forgot", max_requests=5, window_seconds=60)
    user = db.query(User).filter(User.email.ilike(email.strip())).first()
    if user:
        user.reset_token = secrets.token_urlsafe(32)
        db.add(
            Notification(
                user_id=user.id,
                title="Password Reset Requested",
                message="A password reset request was initiated for your account.",
                notif_type="security",
            )
        )
        db.commit()
    return {"message": "If that email is registered, password reset instructions have been dispatched."}


@router.post("/reset-password")
def reset_password(token: str, new_password: str, db: Session = Depends(get_db)):
    if len(new_password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters.")
    user = db.query(User).filter(User.reset_token == token).first()
    if not user:
        raise HTTPException(status_code=400, detail="Invalid or expired password reset token.")
    user.password_hash = hash_password(new_password)
    user.reset_token = None
    db.commit()
    return {"message": "Password updated."}


@router.post("/apply-developer")
def apply_for_developer_role(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if user.role in ("developer", "admin"):
        return {"message": "Account already has developer permissions.", "role": user.role}
    user.role = "developer"
    if not user.developer_profile:
        db.add(DeveloperProfile(user_id=user.id, display_name=user.username, is_verified=False))
    db.commit()
    return {"message": "Developer role activated.", "role": user.role}


@router.get("/me")
def get_me(user: User = Depends(get_current_user)):
    dev = user.developer_profile
    prof = user.profile
    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "role": user.role,
        "is_email_verified": user.is_email_verified,
        "joined_at": user.created_at.isoformat(),
        "profile": {
            "bio": prof.bio if prof else "",
            "avatar_url": prof.avatar_url if prof else None,
            "github_url": prof.github_url if prof else None,
            "discord_url": prof.discord_url if prof else None,
            "website_url": prof.website_url if prof else None,
        },
        "developer": {
            "id": dev.id,
            "display_name": dev.display_name,
            "is_verified": dev.is_verified,
            "total_download_clicks": dev.total_download_clicks,
        } if dev else None,
    }


@router.put("/profile")
def update_profile(payload: ProfileUpdateRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    prof = user.profile
    if not prof:
        prof = UserProfile(user_id=user.id)
        db.add(prof)
    prof.bio = sanitize_text(payload.bio)
    prof.github_url = validate_external_url(payload.github_url)
    prof.discord_url = validate_external_url(payload.discord_url)
    prof.website_url = validate_external_url(payload.website_url)
    if payload.avatar_url:
        prof.avatar_url = sanitize_text(payload.avatar_url)
    db.commit()
    return {"message": "Profile updated."}
