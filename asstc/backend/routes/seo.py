from fastapi import APIRouter, Depends, Response
from sqlalchemy import func
from sqlalchemy.orm import Session

from backend.config import settings
from backend.database import get_db
from backend.models import DeveloperProfile, Launcher, Notification, Review, User
from backend.security import get_current_user

router = APIRouter(tags=["SEO & Notifications"])


@router.get("/api/stats")
def community_statistics(db: Session = Depends(get_db)):
    total_clicks = db.query(func.sum(Launcher.download_clicks)).filter(Launcher.status == "approved").scalar() or 0
    return {
        "approved_launchers": db.query(Launcher).filter(Launcher.status == "approved").count(),
        "verified_developers": db.query(DeveloperProfile).filter(DeveloperProfile.is_verified.is_(True)).count(),
        "registered_members": db.query(User).count(),
        "total_download_clicks": int(total_clicks),
        "community_reviews": db.query(Review).count(),
    }


@router.get("/api/notifications")
def list_user_notifications(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    items = (
        db.query(Notification)
        .filter(Notification.user_id == user.id)
        .order_by(Notification.created_at.desc())
        .limit(25)
        .all()
    )
    unread = sum(1 for n in items if not n.is_read)
    return {
        "unread_count": unread,
        "items": [
            {
                "id": n.id,
                "title": n.title,
                "message": n.message,
                "notif_type": n.notif_type,
                "is_read": n.is_read,
                "created_at": n.created_at.isoformat(),
            }
            for n in items
        ],
    }


@router.post("/api/notifications/read-all")
def mark_all_notifications_read(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    db.query(Notification).filter(Notification.user_id == user.id, Notification.is_read.is_(False)).update(
        {"is_read": True}
    )
    db.commit()
    return {"message": "All notifications marked as read."}


@router.get("/robots.txt", response_class=Response)
def robots_txt():
    content = f"User-agent: *\nAllow: /\nDisallow: /api/admin/\nSitemap: {settings.APP_URL}/sitemap.xml\n"
    return Response(content=content, media_type="text/plain")


@router.get("/sitemap.xml", response_class=Response)
def sitemap_xml(db: Session = Depends(get_db)):
    launchers = db.query(Launcher).filter(Launcher.status == "approved").all()
    urls = [
        f"<url><loc>{settings.APP_URL}/</loc><priority>1.0</priority></url>",
        f"<url><loc>{settings.APP_URL}/#/explore</loc><priority>0.9</priority></url>",
    ]
    for l in launchers:
        urls.append(f"<url><loc>{settings.APP_URL}/#/launcher/{l.slug}</loc><priority>0.8</priority></url>")
    xml = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        + "\n".join(urls)
        + "\n</urlset>"
    )
    return Response(content=xml, media_type="application/xml")
