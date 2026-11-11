from datetime import datetime, timezone
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship
from backend.database import Base


def utcnow():
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(40), unique=True, nullable=False, index=True)
    email = Column(String(120), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(20), nullable=False, default="user")  # guest, user, developer, admin
    is_email_verified = Column(Boolean, default=False, nullable=False)
    is_banned = Column(Boolean, default=False, nullable=False)
    verification_token = Column(String(128), nullable=True)
    reset_token = Column(String(128), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)

    profile = relationship("UserProfile", back_populates="user", uselist=False, cascade="all, delete-orphan")
    developer_profile = relationship("DeveloperProfile", back_populates="user", uselist=False, cascade="all, delete-orphan")
    reviews = relationship("Review", back_populates="user", cascade="all, delete-orphan")
    reports = relationship("Report", back_populates="reporter", cascade="all, delete-orphan")
    notifications = relationship("Notification", back_populates="user", cascade="all, delete-orphan")
    admin_logs = relationship("AdminActivityLog", back_populates="admin", cascade="all, delete-orphan")


class UserProfile(Base):
    __tablename__ = "user_profiles"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    avatar_url = Column(String(500), nullable=True)
    bio = Column(Text, default="", nullable=False)
    github_url = Column(String(300), nullable=True)
    discord_url = Column(String(300), nullable=True)
    website_url = Column(String(300), nullable=True)
    joined_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)

    user = relationship("User", back_populates="profile")


class DeveloperProfile(Base):
    __tablename__ = "developer_profiles"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    display_name = Column(String(80), nullable=False, index=True)
    is_verified = Column(Boolean, default=False, nullable=False)
    verified_at = Column(DateTime(timezone=True), nullable=True)
    github_profile = Column(String(300), nullable=True)
    official_website = Column(String(300), nullable=True)
    total_download_clicks = Column(Integer, default=0, nullable=False)

    user = relationship("User", back_populates="developer_profile")
    launchers = relationship("Launcher", back_populates="developer", cascade="all, delete-orphan")
    verification_requests = relationship("VerificationRequest", back_populates="developer", cascade="all, delete-orphan")


class Category(Base):
    __tablename__ = "categories"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(60), unique=True, nullable=False)
    slug = Column(String(60), unique=True, nullable=False, index=True)
    description = Column(String(255), default="", nullable=False)
    icon_name = Column(String(40), default="box", nullable=False)

    launchers = relationship("Launcher", back_populates="category")


class Launcher(Base):
    __tablename__ = "launchers"

    id = Column(Integer, primary_key=True, index=True)
    slug = Column(String(80), unique=True, nullable=False, index=True)
    name = Column(String(80), unique=True, nullable=False, index=True)
    short_description = Column(String(200), nullable=False)
    full_description = Column(Text, nullable=False)
    developer_id = Column(Integer, ForeignKey("developer_profiles.id", ondelete="CASCADE"), nullable=False)
    category_id = Column(Integer, ForeignKey("categories.id", ondelete="SET NULL"), nullable=True)
    logo_url = Column(String(500), nullable=True)
    latest_version = Column(String(40), nullable=False)
    mc_editions = Column(String(120), nullable=False, default="Java Edition")
    supported_os = Column(String(160), nullable=False, default="Windows, Linux, macOS")
    download_url = Column(String(500), nullable=False)
    github_url = Column(String(500), nullable=True)
    discord_url = Column(String(500), nullable=True)
    website_url = Column(String(500), nullable=True)
    docs_url = Column(String(500), nullable=True)
    installation_guide = Column(Text, default="", nullable=False)
    system_requirements = Column(Text, default="64-bit OS, 4 GB RAM minimum (8 GB recommended), OpenGL 3.2+ GPU, Java 17/21 Runtime", nullable=False)
    status = Column(String(20), default="pending", nullable=False, index=True)  # pending, approved, rejected
    is_featured = Column(Boolean, default=False, nullable=False, index=True)
    download_clicks = Column(Integer, default=0, nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)

    developer = relationship("DeveloperProfile", back_populates="launchers")
    category = relationship("Category", back_populates="launchers")
    screenshots = relationship("LauncherScreenshot", back_populates="launcher", cascade="all, delete-orphan", order_by="LauncherScreenshot.sort_order")
    versions = relationship("LauncherVersion", back_populates="launcher", cascade="all, delete-orphan", order_by="LauncherVersion.released_at.desc()")
    download_links = relationship("DownloadLink", back_populates="launcher", cascade="all, delete-orphan")
    download_events = relationship("DownloadEvent", back_populates="launcher", cascade="all, delete-orphan")
    reviews = relationship("Review", back_populates="launcher", cascade="all, delete-orphan")
    reports = relationship("Report", back_populates="launcher", cascade="all, delete-orphan")


class LauncherScreenshot(Base):
    __tablename__ = "launcher_screenshots"

    id = Column(Integer, primary_key=True, index=True)
    launcher_id = Column(Integer, ForeignKey("launchers.id", ondelete="CASCADE"), nullable=False)
    image_url = Column(String(500), nullable=False)
    caption = Column(String(140), default="", nullable=False)
    sort_order = Column(Integer, default=0, nullable=False)

    launcher = relationship("Launcher", back_populates="screenshots")


class LauncherVersion(Base):
    __tablename__ = "launcher_versions"

    id = Column(Integer, primary_key=True, index=True)
    launcher_id = Column(Integer, ForeignKey("launchers.id", ondelete="CASCADE"), nullable=False)
    version_number = Column(String(40), nullable=False)
    changelog = Column(Text, nullable=False)
    download_url = Column(String(500), nullable=False)
    sha256_hash = Column(String(64), nullable=True)
    released_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)

    launcher = relationship("Launcher", back_populates="versions")


class DownloadLink(Base):
    __tablename__ = "download_links"

    id = Column(Integer, primary_key=True, index=True)
    launcher_id = Column(Integer, ForeignKey("launchers.id", ondelete="CASCADE"), nullable=False)
    platform = Column(String(40), nullable=False)  # Windows, Linux, macOS, Android, iOS, FreeBSD
    label = Column(String(80), nullable=False)
    url = Column(String(500), nullable=False)
    architecture = Column(String(40), default="x86_64 / ARM64", nullable=False)

    launcher = relationship("Launcher", back_populates="download_links")


class DownloadEvent(Base):
    __tablename__ = "download_events"

    id = Column(Integer, primary_key=True, index=True)
    launcher_id = Column(Integer, ForeignKey("launchers.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    platform = Column(String(40), default="All", nullable=False)
    ip_hash = Column(String(64), nullable=False)
    user_agent = Column(String(255), default="", nullable=False)
    clicked_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)

    launcher = relationship("Launcher", back_populates="download_events")


class Review(Base):
    __tablename__ = "reviews"
    __table_args__ = (UniqueConstraint("launcher_id", "user_id", name="uq_launcher_user_review"),)

    id = Column(Integer, primary_key=True, index=True)
    launcher_id = Column(Integer, ForeignKey("launchers.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    rating = Column(Integer, nullable=False)  # 1..5
    comment = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)

    launcher = relationship("Launcher", back_populates="reviews")
    user = relationship("User", back_populates="reviews")


class Report(Base):
    __tablename__ = "reports"

    id = Column(Integer, primary_key=True, index=True)
    launcher_id = Column(Integer, ForeignKey("launchers.id", ondelete="CASCADE"), nullable=False, index=True)
    reporter_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    reason = Column(String(60), nullable=False)  # suspicious_link, broken_url, fake_project, malware_concern
    details = Column(Text, nullable=False)
    status = Column(String(20), default="open", nullable=False)  # open, resolved, dismissed
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)

    launcher = relationship("Launcher", back_populates="reports")
    reporter = relationship("User", back_populates="reports")


class VerificationRequest(Base):
    __tablename__ = "verification_requests"

    id = Column(Integer, primary_key=True, index=True)
    developer_id = Column(Integer, ForeignKey("developer_profiles.id", ondelete="CASCADE"), nullable=False)
    github_profile = Column(String(300), nullable=False)
    official_website = Column(String(300), nullable=False)
    ownership_evidence = Column(Text, nullable=False)
    status = Column(String(20), default="pending", nullable=False)  # pending, approved, rejected
    admin_notes = Column(Text, default="", nullable=False)
    submitted_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    reviewed_at = Column(DateTime(timezone=True), nullable=True)

    developer = relationship("DeveloperProfile", back_populates="verification_requests")


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(120), nullable=False)
    message = Column(Text, nullable=False)
    notif_type = Column(String(40), default="info", nullable=False)  # approval, rejection, verification, security, system
    is_read = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)

    user = relationship("User", back_populates="notifications")


class AdminActivityLog(Base):
    __tablename__ = "admin_activity_logs"

    id = Column(Integer, primary_key=True, index=True)
    admin_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    action = Column(String(80), nullable=False)
    target_type = Column(String(40), nullable=False)
    target_id = Column(Integer, nullable=False)
    details = Column(Text, default="", nullable=False)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)

    admin = relationship("User", back_populates="admin_logs")
