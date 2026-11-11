import os
from datetime import datetime, timezone
from backend.database import Base, SessionLocal, engine
from backend.models import (
    Category,
    DeveloperProfile,
    DownloadLink,
    Launcher,
    LauncherVersion,
    Notification,
    Review,
    User,
    UserProfile,
)
from backend.security import hash_password


def init_and_seed_db():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        if db.query(Category).count() > 0:
            return

        categories = [
            Category(
                name="Modded & Multi-Instance",
                slug="modded-multi-instance",
                description="Manage isolated Minecraft installations, accounts, and mod loaders.",
                icon_name="layers",
            ),
            Category(
                name="Modpack Ecosystem",
                slug="modpack-ecosystem",
                description="One-click modpack discovery, installation, and automatic dependency updates.",
                icon_name="package",
            ),
            Category(
                name="Cross-Platform & Multi-Arch",
                slug="cross-platform-multi-arch",
                description="Native support across x86_64, ARM64, RISC-V, MIPS, and LoongArch systems.",
                icon_name="cpu",
            ),
            Category(
                name="Mobile & Portable",
                slug="mobile-portable",
                description="Run Minecraft: Java Edition on Android, iOS, and portable handhelds.",
                icon_name="smartphone",
            ),
        ]
        db.add_all(categories)
        db.flush()
        cat_map = {c.slug: c.id for c in categories}

        # Section 6: One-Time Secure Administrator Initialization (krish137u@gmail.com)
        # Never hardcode production passwords; read FIRST_ADMIN_EMAIL and FIRST_ADMIN_PASSWORD from environment,
        # hash before storing, create admin only once, and scrub temporary setup secret from os.environ after init.
        admin_email = os.getenv("FIRST_ADMIN_EMAIL", "krish137u@gmail.com").strip().lower()
        admin_username = os.getenv("FIRST_ADMIN_USERNAME", "krish_admin").strip()
        raw_admin_password = os.getenv("FIRST_ADMIN_PASSWORD")
        if not raw_admin_password or raw_admin_password == "YOUR_NEW_STRONG_UNIQUE_PASSWORD":
            import secrets as _sec
            raw_admin_password = _sec.token_urlsafe(32)
        admin_password_hash = hash_password(raw_admin_password)
        # Immediately remove temporary setup password from environment memory
        os.environ.pop("FIRST_ADMIN_PASSWORD", None)
        del raw_admin_password

        admin_user = User(
            username=admin_username,
            email=admin_email,
            password_hash=admin_password_hash,
            role="admin",
            is_email_verified=True,
        )
        db.add(admin_user)
        db.flush()
        db.add(
            UserProfile(
                user_id=admin_user.id,
                bio="BLOCKHUB Platform Security & Moderation Administrator.",
                github_url="https://github.com/PrismLauncher",
                website_url="https://prismlauncher.org/",
            )
        )
        db.add(
            DeveloperProfile(
                user_id=admin_user.id,
                display_name="BLOCKHUB Core Team",
                is_verified=True,
                verified_at=datetime.now(timezone.utc),
                github_profile="https://github.com/PrismLauncher",
                official_website="https://prismlauncher.org/",
            )
        )

        # Grounded real-world open-source launcher maintainer profiles & listings
        seed_records = [
            {
                "username": "prismlauncher",
                "email": "maintainers@prismlauncher.org",
                "display_name": "PrismLauncher",
                "github_profile": "https://github.com/prismlauncher/PrismLauncher",
                "official_website": "https://prismlauncher.org/",
                "slug": "prism-launcher",
                "name": "Prism Launcher",
                "short_description": "An open-source Minecraft launcher with the ability to manage multiple instances, accounts and mods.",
                "full_description": (
                    "Prism Launcher is a custom open-source launcher for Minecraft that allows you to easily manage "
                    "multiple installations of Minecraft at once. Forked from MultiMC with a focus on user freedom, "
                    "free redistributability, and seamless integration with Modrinth and CurseForge modpacks."
                ),
                "category_slug": "modded-multi-instance",
                "latest_version": "11.0",
                "mc_editions": "Java Edition",
                "supported_os": "Windows, Linux, macOS",
                "download_url": "https://github.com/PrismLauncher/PrismLauncher/releases",
                "github_url": "https://github.com/prismlauncher/PrismLauncher",
                "website_url": "https://prismlauncher.org/",
                "docs_url": "https://prismlauncher.org/",
                "installation_guide": (
                    "1. Visit https://prismlauncher.org/ or the official GitHub Releases page.\n"
                    "2. Download the installer for Windows (.exe), macOS (.dmg), or Linux (Flatpak / AppImage / AUR).\n"
                    "3. Sign in with your Microsoft account and create your first isolated Minecraft instance."
                ),
                "is_featured": True,
                "changelog": "Prism Launcher Release 11.0: Updated updater pipeline and improved multi-instance mod management.",
                "platforms": [
                    ("Windows", "Windows Installer / Portable (.exe)", "https://github.com/PrismLauncher/PrismLauncher/releases"),
                    ("Linux", "AppImage / Flatpak / Qt6", "https://github.com/PrismLauncher/PrismLauncher/releases"),
                    ("macOS", "Universal macOS (.dmg)", "https://github.com/PrismLauncher/PrismLauncher/releases"),
                ],
            },
            {
                "username": "modrinth",
                "email": "app@modrinth.com",
                "display_name": "Modrinth",
                "github_profile": "https://github.com/modrinth/code",
                "official_website": "https://modrinth.com/app",
                "slug": "modrinth-app",
                "name": "Modrinth App",
                "short_description": "Tauri-based open-source launcher (codename Theseus) to download and play with favorite mods and modpacks.",
                "full_description": (
                    "The Modrinth App (codename Theseus) is Modrinth's official standalone Rust + Tauri launcher for "
                    "Minecraft: Java Edition. Browse, install, update, and share modpacks and mods directly from the "
                    "Modrinth ecosystem with automatic Java runtime and mod loader provisioning."
                ),
                "category_slug": "modpack-ecosystem",
                "latest_version": "0.23.1",
                "mc_editions": "Java Edition",
                "supported_os": "Windows, macOS, Linux",
                "download_url": "https://modrinth.com/app",
                "github_url": "https://github.com/modrinth/code",
                "website_url": "https://modrinth.com/app",
                "docs_url": "https://docs.modrinth.com/contributing/theseus/",
                "installation_guide": (
                    "1. Download the official installer from https://modrinth.com/app or GitHub Releases.\n"
                    "2. Launch Modrinth App and authenticate your Microsoft account.\n"
                    "3. Open the Discover tab to install verified Modrinth modpacks in one click."
                ),
                "is_featured": True,
                "changelog": "Modrinth App 0.23.1: Reinstalling a shared instance you own now downloads the last version you published.",
                "platforms": [
                    ("Windows", "Windows Setup (.exe)", "https://modrinth.com/app"),
                    ("macOS", "Universal macOS (.dmg)", "https://modrinth.com/app"),
                    ("Linux", "Flathub / AppImage / DEB", "https://modrinth.com/app"),
                ],
            },
            {
                "username": "atlauncher",
                "email": "contact@atlauncher.com",
                "display_name": "ATLauncher",
                "github_profile": "https://github.com/ATLauncher/ATLauncher",
                "official_website": "https://atlauncher.com/",
                "slug": "atlauncher",
                "name": "ATLauncher",
                "short_description": "Simple and easy-to-use Minecraft launcher integrating multiple modpack platforms to install modpacks quickly.",
                "full_description": (
                    "ATLauncher is a cross-platform launcher for Minecraft that integrates multiple modpack ecosystems "
                    "including ATLauncher, Modrinth, and CurseForge so players can download, manage, and export instances effortlessly."
                ),
                "category_slug": "modpack-ecosystem",
                "latest_version": "3.4.41.3",
                "mc_editions": "Java Edition",
                "supported_os": "Windows, macOS, Linux",
                "download_url": "https://atlauncher.com/downloads",
                "github_url": "https://github.com/ATLauncher/ATLauncher",
                "website_url": "https://atlauncher.com/",
                "docs_url": "https://github.com/ATLauncher/ATLauncher",
                "installation_guide": (
                    "1. Download ATLauncher-3.4.41.3.exe or the cross-platform .jar from https://atlauncher.com/downloads.\n"
                    "2. Place portable builds in a dedicated folder and run the setup wizard.\n"
                    "3. Browse the Packs tab to create custom or pre-configured modpack instances."
                ),
                "is_featured": True,
                "changelog": "ATLauncher 3.4.41.3: Updated Windows setup, universal JAR, and modpack dependency verification.",
                "sha256": "9e38e3d1a863e36bdbf0fc3a2617b9f35cba72221ad1757e34efc1ba4a3b0d7b",
                "platforms": [
                    ("Windows", "ATLauncher-3.4.41.3.exe", "https://github.com/ATLauncher/ATLauncher/releases"),
                    ("Linux", "ATLauncher-3.4.41.3.jar", "https://github.com/ATLauncher/ATLauncher/releases"),
                    ("macOS", "ATLauncher-3.4.41.3.zip", "https://github.com/ATLauncher/ATLauncher/releases"),
                ],
            },
            {
                "username": "hmcl_dev",
                "email": "dev@hmcl.net",
                "display_name": "HMCL-dev",
                "github_profile": "https://github.com/HMCL-dev/HMCL",
                "official_website": "https://github.com/HMCL-dev/HMCL",
                "slug": "hmcl",
                "name": "Hello Minecraft! Launcher (HMCL)",
                "short_description": "Open-source cross-platform launcher supporting Forge, NeoForge, Fabric, Quilt, and multi-CPU architectures.",
                "full_description": (
                    "HMCL is a multi-functional, open-source cross-platform Minecraft launcher supporting Mod Management, "
                    "Game Customizing, automatic ModLoader installation (Forge, NeoForge, Cleanroom, Fabric, Legacy Fabric, "
                    "Quilt, LiteLoader, OptiFine), UI customization, and broad CPU architecture support (x86, ARM, RISC-V, MIPS, LoongArch)."
                ),
                "category_slug": "cross-platform-multi-arch",
                "latest_version": "3.17.0.364",
                "mc_editions": "Java Edition",
                "supported_os": "Windows, Linux, macOS, FreeBSD",
                "download_url": "https://github.com/HMCL-dev/HMCL/releases",
                "github_url": "https://github.com/HMCL-dev/HMCL",
                "website_url": "https://github.com/HMCL-dev/HMCL",
                "docs_url": "https://github.com/HMCL-dev/HMCL/blob/main/docs/PLATFORM.md",
                "installation_guide": (
                    "1. Grab the latest HMCL release from https://github.com/HMCL-dev/HMCL/releases.\n"
                    "2. Ensure Java 17+ or OpenJFX is available on your OS architecture.\n"
                    "3. Launch HMCL and configure your preferred ModLoader and theme."
                ),
                "is_featured": False,
                "changelog": "HMCL 3.17.0.364: Multi-architecture improvements across x86, ARM, RISC-V, and NeoForge installer updates.",
                "platforms": [
                    ("Windows", "HMCL Windows (.exe)", "https://github.com/HMCL-dev/HMCL/releases"),
                    ("Linux", "HMCL Universal (.jar / x86 / ARM / RISC-V)", "https://github.com/HMCL-dev/HMCL/releases"),
                    ("macOS", "HMCL macOS Build", "https://github.com/HMCL-dev/HMCL/releases"),
                ],
            },
            {
                "username": "multimc",
                "email": "info@multimc.org",
                "display_name": "MultiMC",
                "github_profile": "https://github.com/MultiMC/Launcher",
                "official_website": "https://multimc.org/",
                "slug": "multimc",
                "name": "MultiMC",
                "short_description": "Custom launcher for Minecraft that manages multiple isolated installations, worlds, and modpacks at once.",
                "full_description": (
                    "MultiMC is a clean, portable custom launcher for Minecraft focused on predictable instance isolation. "
                    "Manage separate Minecraft versions, Java runtimes, world saves, resource packs, and logs in one lightweight interface."
                ),
                "category_slug": "modded-multi-instance",
                "latest_version": "0.6.13",
                "mc_editions": "Java Edition",
                "supported_os": "Windows, macOS, Linux",
                "download_url": "https://multimc.org/",
                "github_url": "https://github.com/MultiMC/Launcher",
                "website_url": "https://multimc.org/",
                "docs_url": "https://github.com/MultiMC/Launcher/wiki/Getting-Started",
                "installation_guide": (
                    "1. Download the archive for your operating system from https://multimc.org/.\n"
                    "2. Extract the archive to a dedicated directory and launch MultiMC.\n"
                    "3. Select your Java runtime and add your Microsoft account."
                ),
                "is_featured": False,
                "changelog": "MultiMC 0.6.13: Added Microsoft account support, modpack platform import updates, and improved Java runtime detection.",
                "platforms": [
                    ("Windows", "Windows 64-bit (.zip)", "https://multimc.org/"),
                    ("Linux", "Linux 64-bit (.tar.gz)", "https://multimc.org/"),
                    ("macOS", "macOS Universal (.tar.gz)", "https://multimc.org/"),
                ],
            },
            {
                "username": "pojavteam",
                "email": "team@pojavlauncher.app",
                "display_name": "PojavLauncherTeam",
                "github_profile": "https://github.com/pojavlauncherteam/pojavlauncher",
                "official_website": "https://github.com/pojavlauncherteam/pojavlauncher",
                "slug": "pojavlauncher",
                "name": "PojavLauncher",
                "short_description": "Minecraft: Java Edition launcher for Android and iOS based on Boardwalk with Forge and Fabric support.",
                "full_description": (
                    "PojavLauncher brings Minecraft: Java Edition to Android and iOS devices based on Boardwalk. "
                    "Capable of launching versions ranging from rd-132211 to 1.21 snapshots, including Combat Test builds "
                    "and modding via Forge and Fabric."
                ),
                "category_slug": "mobile-portable",
                "latest_version": "1.21-snapshot",
                "mc_editions": "Java Edition",
                "supported_os": "Android, iOS",
                "download_url": "https://github.com/pojavlauncherteam/pojavlauncher",
                "github_url": "https://github.com/pojavlauncherteam/pojavlauncher",
                "website_url": "https://github.com/pojavlauncherteam/pojavlauncher",
                "docs_url": "https://github.com/pojavlauncherteam/pojavlauncher",
                "installation_guide": (
                    "1. Visit https://github.com/pojavlauncherteam/pojavlauncher to obtain the Android APK or iOS build instructions.\n"
                    "2. Sign in with an official Microsoft account that owns Minecraft: Java Edition.\n"
                    "3. Select your desired Java version and touch control profile."
                ),
                "is_featured": False,
                "changelog": "Supports Minecraft: Java Edition versions from rd-132211 through 1.21 snapshots with Forge and Fabric modding.",
                "platforms": [
                    ("Android", "Android APK via GitHub", "https://github.com/pojavlauncherteam/pojavlauncher"),
                    ("iOS", "iOS / iPadOS Repository", "https://github.com/pojavlauncherteam/pojavlauncher"),
                ],
            },
        ]

        for item in seed_records:
            u = User(
                username=item["username"],
                email=item["email"],
                password_hash=hash_password(os.getenv("SEED_MAINTAINER_PASSWORD") or os.urandom(24).hex()),
                role="developer",
                is_email_verified=True,
            )
            db.add(u)
            db.flush()

            db.add(
                UserProfile(
                    user_id=u.id,
                    bio=item["short_description"],
                    github_url=item["github_profile"],
                    website_url=item["official_website"],
                )
            )
            dev = DeveloperProfile(
                user_id=u.id,
                display_name=item["display_name"],
                is_verified=True,
                verified_at=datetime.now(timezone.utc),
                github_profile=item["github_profile"],
                official_website=item["official_website"],
                total_download_clicks=0,
            )
            db.add(dev)
            db.flush()

            l = Launcher(
                slug=item["slug"],
                name=item["name"],
                short_description=item["short_description"],
                full_description=item["full_description"],
                developer_id=dev.id,
                category_id=cat_map[item["category_slug"]],
                logo_url=None,
                latest_version=item["latest_version"],
                mc_editions=item["mc_editions"],
                supported_os=item["supported_os"],
                download_url=item["download_url"],
                github_url=item["github_url"],
                website_url=item["website_url"],
                docs_url=item["docs_url"],
                installation_guide=item["installation_guide"],
                status="approved",
                is_featured=item["is_featured"],
                download_clicks=0,
            )
            db.add(l)
            db.flush()

            db.add(
                LauncherVersion(
                    launcher_id=l.id,
                    version_number=item["latest_version"],
                    changelog=item["changelog"],
                    download_url=item["download_url"],
                    sha256_hash=item.get("sha256"),
                )
            )
            for plat, label, url in item["platforms"]:
                db.add(
                    DownloadLink(
                        launcher_id=l.id,
                        platform=plat,
                        label=label,
                        url=url,
                    )
                )

            db.add(
                Review(
                    launcher_id=l.id,
                    user_id=admin_user.id,
                    rating=5,
                    comment=f"Verified open-source repository ({item['github_url']}) and active release cycle.",
                )
            )

        db.commit()
    finally:
        db.close()


if __name__ == "__main__":
    init_and_seed_db()
    print("BLOCKHUB database initialized and seeded.")
