from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import (
    AdminActivityLog,
    Category,
    DeveloperProfile,
    DownloadEvent,
    Launcher,
    Notification,
    Report,
    User,
    VerificationRequest,
)
from backend.schemas import CategoryCreateRequest
from backend.security import require_admin, sanitize_text

router = APIRouter(prefix="/api/admin", tags=["Admin Moderation"])


def log_admin_action(db: Session, admin_id: int, action: str, target_type: str, target_id: int, details: str = ""):
    db.add(
        AdminActivityLog(
            admin_id=admin_id,
            action=action,
            target_type=target_type,
            target_id=target_id,
            details=details,
        )
    )


@router.get("/overview")
def admin_overview(admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    total_clicks = db.query(func.sum(Launcher.download_clicks)).scalar() or 0
    return {
        "metrics": {
            "total_users": db.query(User).count(),
            "total_developers": db.query(DeveloperProfile).count(),
            "verified_developers": db.query(DeveloperProfile).filter(DeveloperProfile.is_verified.is_(True)).count(),
            "total_launchers": db.query(Launcher).count(),
            "pending_launchers": db.query(Launcher).filter(Launcher.status == "pending").count(),
            "approved_launchers": db.query(Launcher).filter(Launcher.status == "approved").count(),
            "open_reports": db.query(Report).filter(Report.status == "open").count(),
            "pending_verifications": db.query(VerificationRequest).filter(VerificationRequest.status == "pending").count(),
            "total_download_clicks": int(total_clicks),
            "download_events_logged": db.query(DownloadEvent).count(),
        },
        "pending_submissions": [
            {
                "id": l.id,
                "slug": l.slug,
                "name": l.name,
                "developer": l.developer.display_name if l.developer else "Unknown",
                "latest_version": l.latest_version,
                "download_url": l.download_url,
                "github_url": l.github_url,
                "created_at": l.created_at.isoformat(),
            }
            for l in db.query(Launcher).filter(Launcher.status == "pending").order_by(Launcher.created_at.asc()).all()
        ],
        "open_reports": [
            {
                "id": r.id,
                "launcher_id": r.launcher_id,
                "launcher_name": r.launcher.name if r.launcher else "Deleted",
                "reporter": r.reporter.username if r.reporter else "User",
                "reason": r.reason,
                "details": r.details,
                "status": r.status,
                "created_at": r.created_at.isoformat(),
            }
            for r in db.query(Report).order_by(Report.created_at.desc()).limit(30).all()
        ],
        "verification_requests": [
            {
                "id": vr.id,
                "developer_id": vr.developer_id,
                "developer_name": vr.developer.display_name if vr.developer else "Unknown",
                "github_profile": vr.github_profile,
                "official_website": vr.official_website,
                "ownership_evidence": vr.ownership_evidence,
                "status": vr.status,
                "submitted_at": vr.submitted_at.isoformat(),
            }
            for vr in db.query(VerificationRequest).order_by(VerificationRequest.submitted_at.desc()).all()
        ],
        "recent_logs": [
            {
                "id": log.id,
                "admin": log.admin.username if log.admin else "admin",
                "action": log.action,
                "target_type": log.target_type,
                "target_id": log.target_id,
                "details": log.details,
                "created_at": log.created_at.isoformat(),
            }
            for log in db.query(AdminActivityLog).order_by(AdminActivityLog.created_at.desc()).limit(25).all()
        ],
    }


@router.get("/users")
def list_all_users(admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    users = db.query(User).order_by(User.created_at.desc()).all()
    return [
        {
            "id": u.id,
            "username": u.username,
            "email": u.email,
            "role": u.role,
            "is_email_verified": u.is_email_verified,
            "is_banned": u.is_banned,
            "is_verified_developer": u.developer_profile.is_verified if u.developer_profile else False,
            "created_at": u.created_at.isoformat(),
        }
        for u in users
    ]


@router.post("/launchers/{launcher_id}/moderate")
def moderate_launcher(
    launcher_id: int,
    decision: str,
    reason: str = "",
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    if decision not in ("approved", "rejected"):
        raise HTTPException(status_code=400, detail="Decision must be 'approved' or 'rejected'.")

    launcher = db.query(Launcher).filter(Launcher.id == launcher_id).first()
    if not launcher:
        raise HTTPException(status_code=404, detail="Launcher not found.")

    launcher.status = decision
    log_admin_action(db, admin.id, f"launcher_{decision}", "launcher", launcher.id, sanitize_text(reason))

    if launcher.developer and launcher.developer.user_id:
        db.add(
            Notification(
                user_id=launcher.developer.user_id,
                title=f"Launcher {decision.capitalize()}: {launcher.name}",
                message=(
                    f"Your launcher '{launcher.name}' has been {decision} by BLOCKHUB moderation. "
                    + (f"Note: {sanitize_text(reason)}" if reason else "")
                ),
                notif_type="approval" if decision == "approved" else "rejection",
            )
        )
    db.commit()
    return {"message": f"Launcher '{launcher.name}' marked as {decision}.", "status": launcher.status}


@router.post("/launchers/{launcher_id}/feature")
def toggle_featured_launcher(
    launcher_id: int,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    launcher = db.query(Launcher).filter(Launcher.id == launcher_id).first()
    if not launcher:
        raise HTTPException(status_code=404, detail="Launcher not found.")
    launcher.is_featured = not launcher.is_featured
    log_admin_action(
        db,
        admin.id,
        "toggle_featured",
        "launcher",
        launcher.id,
        f"is_featured={launcher.is_featured}",
    )
    db.commit()
    return {"message": "Featured status updated.", "is_featured": launcher.is_featured}


@router.post("/users/{user_id}/ban")
def toggle_ban_user(user_id: int, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    target = db.query(User).filter(User.id == user_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="User not found.")
    if target.id == admin.id:
        raise HTTPException(status_code=400, detail="Administrators cannot ban themselves.")
    target.is_banned = not target.is_banned
    log_admin_action(db, admin.id, "toggle_ban_user", "user", target.id, f"is_banned={target.is_banned}")
    db.commit()
    return {"message": "User ban status updated.", "is_banned": target.is_banned}


@router.post("/verifications/{req_id}/review")
def review_verification_request(
    req_id: int,
    decision: str,
    notes: str = "",
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    if decision not in ("approved", "rejected"):
        raise HTTPException(status_code=400, detail="Decision must be 'approved' or 'rejected'.")
    vr = db.query(VerificationRequest).filter(VerificationRequest.id == req_id).first()
    if not vr:
        raise HTTPException(status_code=404, detail="Verification request not found.")

    vr.status = decision
    vr.admin_notes = sanitize_text(notes)
    vr.reviewed_at = datetime.now(timezone.utc)

    if vr.developer:
        vr.developer.is_verified = decision == "approved"
        if decision == "approved":
            vr.developer.verified_at = datetime.now(timezone.utc)
        db.add(
            Notification(
                user_id=vr.developer.user_id,
                title=f"Developer Verification {decision.capitalize()}",
                message=f"Your Verified Developer badge request was {decision}.",
                notif_type="verification",
            )
        )

    log_admin_action(db, admin.id, f"verification_{decision}", "verification_request", vr.id, vr.admin_notes)
    db.commit()
    return {"message": f"Verification request {decision}.", "status": vr.status}


@router.post("/reports/{report_id}/resolve")
def resolve_report(
    report_id: int,
    status_value: str = "resolved",
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    rep = db.query(Report).filter(Report.id == report_id).first()
    if not rep:
        raise HTTPException(status_code=404, detail="Report not found.")
    rep.status = status_value if status_value in ("resolved", "dismissed") else "resolved"
    log_admin_action(db, admin.id, f"report_{rep.status}", "report", rep.id, rep.reason)
    db.commit()
    return {"message": f"Report marked as {rep.status}."}


@router.post("/categories", status_code=201)
def create_category(
    payload: CategoryCreateRequest,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    if db.query(Category).filter((Category.slug == payload.slug) | (Category.name == payload.name)).first():
        raise HTTPException(status_code=409, detail="Category already exists.")
    cat = Category(
        name=sanitize_text(payload.name),
        slug=payload.slug,
        description=sanitize_text(payload.description),
        icon_name=sanitize_text(payload.icon_name),
    )
    db.add(cat)
    db.commit()
    db.refresh(cat)
    log_admin_action(db, admin.id, "create_category", "category", cat.id, cat.name)
    db.commit()
    return {"id": cat.id, "name": cat.name, "slug": cat.slug}
