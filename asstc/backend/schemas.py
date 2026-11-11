from typing import List, Optional
from pydantic import BaseModel, EmailStr, Field


class RegisterRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=32, pattern=r"^[a-zA-Z0-9_-]+$")
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)
    role: str = Field(default="user", pattern=r"^user$")
    accept_terms: bool = True


class LoginRequest(BaseModel):
    identifier: str = Field(..., min_length=3, max_length=120)
    password: str = Field(..., min_length=1, max_length=128)
    remember_me: bool = False


class ProfileUpdateRequest(BaseModel):
    bio: str = Field(default="", max_length=600)
    github_url: Optional[str] = None
    discord_url: Optional[str] = None
    website_url: Optional[str] = None
    avatar_url: Optional[str] = None


class LauncherSubmitRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=80)
    short_description: str = Field(..., min_length=10, max_length=200)
    full_description: str = Field(..., min_length=20, max_length=8000)
    category_slug: str = Field(default="modded-multi-instance")
    latest_version: str = Field(..., min_length=1, max_length=40)
    mc_editions: str = Field(default="Java Edition", max_length=120)
    supported_os: str = Field(default="Windows, Linux, macOS", max_length=160)
    download_url: str = Field(..., min_length=8, max_length=500)
    github_url: Optional[str] = None
    discord_url: Optional[str] = None
    website_url: Optional[str] = None
    docs_url: Optional[str] = None
    logo_url: Optional[str] = None
    screenshots: List[str] = []
    installation_guide: str = Field(default="", max_length=4000)
    system_requirements: str = Field(
        default="64-bit OS, 4 GB RAM minimum (8 GB recommended), OpenGL 3.2+ GPU, Java 17/21 Runtime",
        max_length=1000,
    )


class VersionPublishRequest(BaseModel):
    version_number: str = Field(..., min_length=1, max_length=40)
    changelog: str = Field(..., min_length=5, max_length=4000)
    download_url: str = Field(..., min_length=8, max_length=500)
    sha256_hash: Optional[str] = Field(default=None, max_length=64)


class ReviewCreateRequest(BaseModel):
    rating: int = Field(..., ge=1, le=5)
    comment: str = Field(..., min_length=5, max_length=1500)


class ReportCreateRequest(BaseModel):
    reason: str = Field(..., pattern=r"^(suspicious_link|broken_url|fake_project|malware_concern)$")
    details: str = Field(..., min_length=10, max_length=2000)


class VerificationCreateRequest(BaseModel):
    github_profile: str = Field(..., min_length=10, max_length=300)
    official_website: str = Field(..., min_length=8, max_length=300)
    ownership_evidence: str = Field(..., min_length=15, max_length=2000)


class CategoryCreateRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=60)
    slug: str = Field(..., min_length=2, max_length=60, pattern=r"^[a-z0-9-]+$")
    description: str = Field(default="", max_length=255)
    icon_name: str = Field(default="layers", max_length=40)
