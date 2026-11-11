import hashlib
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import (
    Category,
    DeveloperProfile,
    DownloadEvent,
    Launcher,
    Report,
    Review,
    User,
)
from backend.schemas import ReportCreateRequest, ReviewCreateRequest
from backend.security import (
    enforce_rate_limit,
    get_current_user,
    get_current_user_optional,
    sanitize_text,
)

router = APIRouter(prefix="/api/launchers", tags=["Launchers"])


def serialize_launcher_card(launcher: Launcher, db: Session) -> dict:
    avg_rating = (
        db.query(func.avg(Review.rating)).filter(Review.launcher_id == launcher.id).scalar() or 0.0
    )
    review_count = db.query(func.count(Review.id)).filter(Review.launcher_id == launcher.id).scalar() or 0
    return {
        "id": launcher.id,
        "slug": launcher.slug,
        "name": launcher.name,
        "short_description": launcher.short_description,
        "logo_url": launcher.logo_url,
        "latest_version": launcher.latest_version,
        "mc_editions": launcher.mc_editions,
        "supported_os": [s.strip() for s in launcher.supported_os.split(",") if s.strip()],
        "download_clicks": launcher.download_clicks,
        "is_featured": launcher.is_featured,
        "status": launcher.status,
        "category": {
            "name": launcher.category.name,
            "slug": launcher.category.slug,
        } if launcher.category else None,
        "developer": {
            "id": launcher.developer.id,
            "display_name": launcher.developer.display_name,
            "is_verified": launcher.developer.is_verified,
        } if launcher.developer else None,
        "rating_avg": round(float(avg_rating), 1),
        "review_count": review_count,
        "updated_at": launcher.updated_at.isoformat(),
    }


@router.get("")
def list_launchers(
    q: Optional[str] = Query(default=None, description="Search query"),
    category: Optional[str] = Query(default=None),
    platform: Optional[str] = Query(default=None),
    edition: Optional[str] = Query(default=None),
    verified_only: bool = Query(default=False),
    sort: str = Query(default="downloads", pattern=r"^(downloads|newest|name|featured)$"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=12, ge=1, le=50),
    db: Session = Depends(get_db),
):
    query = db.query(Launcher).filter(Launcher.status == "approved")

    if q and q.strip():
        term = f"%{q.strip()}%"
        query = query.filter(
            or_(
                Launcher.name.ilike(term),
                Launcher.short_description.ilike(term),
                Launcher.full_description.ilike(term),
                Launcher.supported_os.ilike(term),
            )
        )
    if category and category != "all":
        query = query.join(Category).filter(Category.slug == category)
    if platform and platform != "all":
        query = query.filter(Launcher.supported_os.ilike(f"%{platform}%"))
    if edition and edition != "all":
        query = query.filter(Launcher.mc_editions.ilike(f"%{edition}%"))
    if verified_only:
        query = query.join(DeveloperProfile).filter(DeveloperProfile.is_verified.is_(True))

    if sort == "downloads":
        query = query.order_by(Launcher.download_clicks.desc(), Launcher.id.asc())
    elif sort == "newest":
        query = query.order_by(Launcher.created_at.desc())
    elif sort == "featured":
        query = query.order_by(Launcher.is_featured.desc(), Launcher.download_clicks.desc())
    else:
        query = query.order_by(Launcher.name.asc())

    total = query.count()
    items = query.offset((page - 1) * page_size).limit(page_size).all()
    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": [serialize_launcher_card(item, db) for item in items],
    }


@router.get("/categories")
def list_categories(db: Session = Depends(get_db)):
    cats = db.query(Category).order_by(Category.name.asc()).all()
    return [
        {
            "id": c.id,
            "name": c.name,
            "slug": c.slug,
            "description": c.description,
            "icon_name": c.icon_name,
            "count": db.query(Launcher).filter(Launcher.category_id == c.id, Launcher.status == "approved").count(),
        }
        for c in cats
    ]


@router.get("/{slug}")
def get_launcher_details(slug: str, db: Session = Depends(get_db)):
    launcher = db.query(Launcher).filter(Launcher.slug == slug, Launcher.status == "approved").first()
    if not launcher:
        raise HTTPException(status_code=404, detail="Launcher not found or pending moderation.")

    card = serialize_launcher_card(launcher, db)
    card.update(
        {
            "full_description": launcher.full_description,
            "download_url": launcher.download_url,
            "github_url": launcher.github_url,
            "discord_url": launcher.discord_url,
            "website_url": launcher.website_url,
            "docs_url": launcher.docs_url,
            "installation_guide": launcher.installation_guide,
            "system_requirements": launcher.system_requirements,
            "screenshots": [
                {"id": s.id, "image_url": s.image_url, "caption": s.caption}
                for s in launcher.screenshots
            ],
            "versions": [
                {
                    "id": v.id,
                    "version_number": v.version_number,
                    "changelog": v.changelog,
                    "download_url": v.download_url,
                    "sha256_hash": v.sha256_hash,
                    "released_at": v.released_at.isoformat(),
                }
                for v in launcher.versions
            ],
            "download_links": [
                {
                    "id": dl.id,
                    "platform": dl.platform,
                    "label": dl.label,
                    "url": dl.url,
                    "architecture": dl.architecture,
                }
                for dl in launcher.download_links
            ],
            "reviews": [
                {
                    "id": r.id,
                    "username": r.user.username if r.user else "User",
                    "rating": r.rating,
                    "comment": r.comment,
                    "created_at": r.created_at.isoformat(),
                }
                for r in launcher.reviews
            ],
        }
    )
    return card


@router.get("/{slug}/download-info")
def get_download_confirmation(slug: str, db: Session = Depends(get_db)):
    launcher = db.query(Launcher).filter(Launcher.slug == slug, Launcher.status == "approved").first()
    if not launcher:
        raise HTTPException(status_code=404, detail="Launcher not found.")

    latest_ver = launcher.versions[0] if launcher.versions else None
    return {
        "launcher_name": launcher.name,
        "slug": launcher.slug,
        "latest_version": launcher.latest_version,
        "developer_name": launcher.developer.display_name if launcher.developer else "Unknown",
        "developer_verified": launcher.developer.is_verified if launcher.developer else False,
        "official_download_url": launcher.download_url,
        "github_url": launcher.github_url,
        "sha256_hash": latest_ver.sha256_hash if latest_ver else None,
        "security_notice": (
            "SECURITY NOTICE: BLOCKHUB indexes external download links provided by launcher developers. "
            "BLOCKHUB never claims that an external file is safe merely because it is listed. "
            "Always verify the official repository URL, inspect SHA-256 checksums, and scan executable files before running them."
        ),
    }


@router.post("/{slug}/download-click")
def record_download_click(
    slug: str,
    request: Request,
    platform: str = "All",
    user: Optional[User] = Depends(get_current_user_optional),
    db: Session = Depends(get_db),
):
    enforce_rate_limit(request, "download_click", max_requests=30, window_seconds=60)
    launcher = db.query(Launcher).filter(Launcher.slug == slug, Launcher.status == "approved").first()
    if not launcher:
        raise HTTPException(status_code=404, detail="Launcher not found.")

    client_ip = request.client.host if request.client else "127.0.0.1"
    ip_hash = hashlib.sha256(client_ip.encode("utf-8")).hexdigest()
    ua = (request.headers.get("user-agent") or "")[:250]

    launcher.download_clicks += 1
    if launcher.developer:
        launcher.developer.total_download_clicks += 1

    event = DownloadEvent(
        launcher_id=launcher.id,
        user_id=user.id if user else None,
        platform=sanitize_text(platform)[:40],
        ip_hash=ip_hash,
        user_agent=ua,
    )
    db.add(event)
    db.commit()

    return {
        "message": "Download click recorded.",
        "download_clicks": launcher.download_clicks,
        "redirect_url": launcher.download_url,
        "security_notice": "External link opened. BLOCKHUB does not host or guarantee third-party binaries.",
    }


@router.post("/{slug}/reviews", status_code=201)
def create_review(
    slug: str,
    payload: ReviewCreateRequest,
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    enforce_rate_limit(request, "review_submit", max_requests=10, window_seconds=60)
    launcher = db.query(Launcher).filter(Launcher.slug == slug, Launcher.status == "approved").first()
    if not launcher:
        raise HTTPException(status_code=404, detail="Launcher not found.")

    existing = db.query(Review).filter(Review.launcher_id == launcher.id, Review.user_id == user.id).first()
    if existing:
        existing.rating = payload.rating
        existing.comment = sanitize_text(payload.comment)
        db.commit()
        return {"message": "Review updated.", "review_id": existing.id}

    rev = Review(
        launcher_id=launcher.id,
        user_id=user.id,
        rating=payload.rating,
        comment=sanitize_text(payload.comment),
    )
    db.add(rev)
    db.commit()
    db.refresh(rev)
    return {"message": "Review posted.", "review_id": rev.id}


@router.post("/{slug}/report", status_code=201)
def report_launcher(
    slug: str,
    payload: ReportCreateRequest,
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    enforce_rate_limit(request, "report_submit", max_requests=5, window_seconds=60)
    launcher = db.query(Launcher).filter(Launcher.slug == slug).first()
    if not launcher:
        raise HTTPException(status_code=404, detail="Launcher not found.")

    rep = Report(
        launcher_id=launcher.id,
        reporter_id=user.id,
        reason=payload.reason,
        details=sanitize_text(payload.details),
        status="open",
    )
    db.add(rep)
    db.commit()
    db.refresh(rep)
    return {"message": "Report submitted to BLOCKHUB moderation.", "report_id": rep.id}


@router.get("/developers/{username}")
def get_public_developer_profile(username: str, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username.ilike(username.strip()), User.is_banned.is_(False)).first()
    if not user:
        raise HTTPException(status_code=404, detail="Developer profile not found.")
    dev = user.developer_profile
    prof = user.profile
    published = (
        db.query(Launcher)
        .filter(Launcher.developer_id == dev.id, Launcher.status == "approved")
        .order_by(Launcher.download_clicks.desc())
        .all()
        if dev
        else []
    )
    return {
        "username": user.username,
        "display_name": dev.display_name if dev else user.username,
        "is_verified": dev.is_verified if dev else False,
        "joined_at": user.created_at.isoformat(),
        "bio": prof.bio if prof else "",
        "github_url": (dev.github_profile if dev and dev.github_profile else (prof.github_url if prof else None)),
        "discord_url": prof.discord_url if prof else None,
        "website_url": (dev.official_website if dev and dev.official_website else (prof.website_url if prof else None)),
        "published_launchers": [serialize_launcher_card(l, db) for l in published],
    }
