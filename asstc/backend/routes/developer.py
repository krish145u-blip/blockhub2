import re
from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import (
    Category,
    DeveloperProfile,
    Launcher,
    LauncherScreenshot,
    LauncherVersion,
    Notification,
    User,
    VerificationRequest,
)
from backend.schemas import (
    LauncherSubmitRequest,
    VerificationCreateRequest,
    VersionPublishRequest,
)
from backend.security import (
    enforce_rate_limit,
    require_developer,
    sanitize_text,
    save_safe_image,
    validate_external_url,
)

router = APIRouter(prefix="/api/developer", tags=["Developer Dashboard"])


def slugify(text: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return slug or "launcher"


def ensure_dev_profile(user: User, db: Session) -> DeveloperProfile:
    if user.developer_profile:
        return user.developer_profile
    dev = DeveloperProfile(user_id=user.id, display_name=user.username, is_verified=False)
    db.add(dev)
    db.commit()
    db.refresh(dev)
    return dev


@router.get("/dashboard")
def developer_dashboard(user: User = Depends(require_developer), db: Session = Depends(get_db)):
    dev = ensure_dev_profile(user, db)
    launchers = db.query(Launcher).filter(Launcher.developer_id == dev.id).order_by(Launcher.created_at.desc()).all()
    total_clicks = sum(l.download_clicks for l in launchers)
    return {
        "developer": {
            "id": dev.id,
            "display_name": dev.display_name,
            "is_verified": dev.is_verified,
            "github_profile": dev.github_profile,
            "official_website": dev.official_website,
            "total_download_clicks": total_clicks,
        },
        "stats": {
            "total_launchers": len(launchers),
            "approved_launchers": sum(1 for l in launchers if l.status == "approved"),
            "pending_launchers": sum(1 for l in launchers if l.status == "pending"),
            "total_download_clicks": total_clicks,
        },
        "launchers": [
            {
                "id": l.id,
                "slug": l.slug,
                "name": l.name,
                "latest_version": l.latest_version,
                "status": l.status,
                "download_clicks": l.download_clicks,
                "is_featured": l.is_featured,
                "updated_at": l.updated_at.isoformat(),
            }
            for l in launchers
        ],
    }


@router.post("/launchers", status_code=201)
def submit_launcher(
    payload: LauncherSubmitRequest,
    request: Request,
    user: User = Depends(require_developer),
    db: Session = Depends(get_db),
):
    enforce_rate_limit(request, "submit_launcher", max_requests=10, window_seconds=60)
    dev = ensure_dev_profile(user, db)

    base_slug = slugify(payload.name)
    if db.query(Launcher).filter((Launcher.slug == base_slug) | (Launcher.name.ilike(payload.name.strip()))).first():
        raise HTTPException(status_code=409, detail="A launcher with this name or slug already exists.")

    cat = db.query(Category).filter(Category.slug == payload.category_slug).first()

    launcher = Launcher(
        slug=base_slug,
        name=sanitize_text(payload.name),
        short_description=sanitize_text(payload.short_description),
        full_description=sanitize_text(payload.full_description),
        developer_id=dev.id,
        category_id=cat.id if cat else None,
        logo_url=sanitize_text(payload.logo_url or ""),
        latest_version=sanitize_text(payload.latest_version),
        mc_editions=sanitize_text(payload.mc_editions),
        supported_os=sanitize_text(payload.supported_os),
        download_url=validate_external_url(payload.download_url, required=True),
        github_url=validate_external_url(payload.github_url),
        discord_url=validate_external_url(payload.discord_url),
        website_url=validate_external_url(payload.website_url),
        docs_url=validate_external_url(payload.docs_url),
        installation_guide=sanitize_text(payload.installation_guide),
        system_requirements=sanitize_text(payload.system_requirements),
        status="pending",
    )
    db.add(launcher)
    db.flush()

    db.add(
        LauncherVersion(
            launcher_id=launcher.id,
            version_number=launcher.latest_version,
            changelog="Initial release submitted to BLOCKHUB.",
            download_url=launcher.download_url,
        )
    )

    for idx, img_url in enumerate(payload.screenshots[:8]):
        if img_url.strip():
            db.add(
                LauncherScreenshot(
                    launcher_id=launcher.id,
                    image_url=sanitize_text(img_url),
                    caption=f"{launcher.name} screenshot {idx + 1}",
                    sort_order=idx,
                )
            )

    # Notify admins
    admins = db.query(User).filter(User.role == "admin").all()
    for admin in admins:
        db.add(
            Notification(
                user_id=admin.id,
                title="New Launcher Pending Approval",
                message=f"{dev.display_name} submitted '{launcher.name}' (v{launcher.latest_version}) for moderation.",
                notif_type="system",
            )
        )

    db.commit()
    db.refresh(launcher)
    return {
        "message": "Launcher submitted and queued for administrator approval.",
        "launcher_id": launcher.id,
        "slug": launcher.slug,
        "status": launcher.status,
    }


@router.put("/launchers/{launcher_id}")
def edit_launcher(
    launcher_id: int,
    payload: LauncherSubmitRequest,
    user: User = Depends(require_developer),
    db: Session = Depends(get_db),
):
    dev = ensure_dev_profile(user, db)
    launcher = db.query(Launcher).filter(Launcher.id == launcher_id).first()
    if not launcher:
        raise HTTPException(status_code=404, detail="Launcher not found.")
    if launcher.developer_id != dev.id and user.role != "admin":
        raise HTTPException(status_code=403, detail="You can only edit your own launcher listings.")

    launcher.short_description = sanitize_text(payload.short_description)
    launcher.full_description = sanitize_text(payload.full_description)
    launcher.latest_version = sanitize_text(payload.latest_version)
    launcher.mc_editions = sanitize_text(payload.mc_editions)
    launcher.supported_os = sanitize_text(payload.supported_os)
    launcher.download_url = validate_external_url(payload.download_url, required=True)
    launcher.github_url = validate_external_url(payload.github_url)
    launcher.discord_url = validate_external_url(payload.discord_url)
    launcher.website_url = validate_external_url(payload.website_url)
    launcher.docs_url = validate_external_url(payload.docs_url)
    launcher.installation_guide = sanitize_text(payload.installation_guide)
    launcher.system_requirements = sanitize_text(payload.system_requirements)
    db.commit()
    return {"message": "Launcher listing updated.", "slug": launcher.slug}


@router.delete("/launchers/{launcher_id}")
def delete_launcher(launcher_id: int, user: User = Depends(require_developer), db: Session = Depends(get_db)):
    dev = ensure_dev_profile(user, db)
    launcher = db.query(Launcher).filter(Launcher.id == launcher_id).first()
    if not launcher:
        raise HTTPException(status_code=404, detail="Launcher not found.")
    if launcher.developer_id != dev.id and user.role != "admin":
        raise HTTPException(status_code=403, detail="Not authorized to delete this listing.")

    db.delete(launcher)
    db.commit()
    return {"message": "Launcher deleted."}


@router.post("/launchers/{launcher_id}/versions", status_code=201)
def publish_version(
    launcher_id: int,
    payload: VersionPublishRequest,
    user: User = Depends(require_developer),
    db: Session = Depends(get_db),
):
    dev = ensure_dev_profile(user, db)
    launcher = db.query(Launcher).filter(Launcher.id == launcher_id).first()
    if not launcher or (launcher.developer_id != dev.id and user.role != "admin"):
        raise HTTPException(status_code=403, detail="Not authorized to publish versions for this launcher.")

    clean_url = validate_external_url(payload.download_url, required=True)
    ver = LauncherVersion(
        launcher_id=launcher.id,
        version_number=sanitize_text(payload.version_number),
        changelog=sanitize_text(payload.changelog),
        download_url=clean_url,
        sha256_hash=sanitize_text(payload.sha256_hash or "") or None,
    )
    launcher.latest_version = ver.version_number
    launcher.download_url = clean_url
    db.add(ver)
    db.commit()
    return {"message": f"Version {ver.version_number} published.", "latest_version": launcher.latest_version}


@router.post("/upload-image")
async def upload_launcher_image(
    file: UploadFile = File(...),
    user: User = Depends(require_developer),
):
    url = await save_safe_image(file)
    return {"url": url, "message": "Image validated and uploaded safely."}


@router.post("/verification-request", status_code=201)
def request_developer_verification(
    payload: VerificationCreateRequest,
    user: User = Depends(require_developer),
    db: Session = Depends(get_db),
):
    dev = ensure_dev_profile(user, db)
    if dev.is_verified:
        return {"message": "Developer account is already verified."}

    req = VerificationRequest(
        developer_id=dev.id,
        github_profile=validate_external_url(payload.github_profile, required=True),
        official_website=validate_external_url(payload.official_website, required=True),
        ownership_evidence=sanitize_text(payload.ownership_evidence),
        status="pending",
    )
    db.add(req)
    db.commit()
    db.refresh(req)
    return {"message": "Verification request submitted for admin review.", "request_id": req.id}
