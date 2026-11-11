# BLOCKHUB — Production-Ready Public Minecraft Launcher Platform

**Tagline:** `DISCOVER. PUBLISH. PLAY.`

BLOCKHUB is a public, full-stack Minecraft launcher discovery and publishing platform connecting Minecraft players with verified open-source and community launcher developers worldwide.

## 1. Complete Architecture & Module Guide

- `backend/config.py` — Reads all secrets, database URLs, and initial administrator bootstrap variables (`FIRST_ADMIN_EMAIL`, `FIRST_ADMIN_PASSWORD`) from server-side environment variables with zero hardcoded secrets.
- `backend/database.py` — Configures the SQLAlchemy 2.0 engine supporting PostgreSQL in production and SQLite (`PRAGMA foreign_keys=ON`) in local Windows VS Code development.
- `backend/models.py` — Defines all 14 relational models: `User`, `UserProfile`, `DeveloperProfile`, `Category`, `Launcher`, `LauncherScreenshot`, `LauncherVersion`, `DownloadLink`, `DownloadEvent`, `Review`, `Report`, `VerificationRequest`, `Notification`, and `AdminActivityLog`.
- `backend/security.py` — Implements PBKDF2-HMAC-SHA256 password hashing (260,000 iterations), JWT HttpOnly/Secure session cookies, HMAC-SHA256 CSRF tokens, sliding-window rate limiting, and magic-byte image upload validation (PNG/JPG/WEBP <= 5 MB; executable binaries strictly rejected).
- `backend/seed.py` — Performs one-time administrator initialization for `FIRST_ADMIN_EMAIL=krish137u@gmail.com`, hashes `FIRST_ADMIN_PASSWORD`, immediately scrubs `FIRST_ADMIN_PASSWORD` from process environment memory, and seeds 6 verified open-source launchers.
- `backend/routes/auth.py` — Handles registration (strictly preventing public assignment of `admin` role), login, logout, email verification, password reset, and profile editing.
- `backend/routes/launchers.py` — Serves public launcher discovery, search, filtering, pagination, launcher detail views, public developer profiles, the mandatory download security interstitial, click telemetry, reviews, and suspicious link reports.
- `backend/routes/developer.py` — Provides developer dashboard metrics, new launcher submissions (`pending` moderation status), version/changelog publishing, safe image uploads, and Verified Developer badge applications.
- `backend/routes/admin.py` — Protects all moderation endpoints behind `require_admin`, enabling launcher approval/rejection, featured toggles, account bans, developer verification approvals, report resolution, and immutable audit logging.
- `backend/routes/seo.py` — Serves dynamic `/sitemap.xml`, `/robots.txt`, community statistics, and in-app notifications.
- `backend/services/logging_monitor.py` — Configures rotating file and console logs (`logs/blockhub.log`).
- `migrations/run_migrations.py` — Verifies and initializes all 14 relational tables.
- `deploy/nginx_blockhub.conf`, `deploy/blockhub.service`, `deploy/backup_db.sh`, `deploy/deploy_update.sh` — Production Linux VPS configs for Nginx + Let's Encrypt HTTPS, systemd daemon management, automated daily PostgreSQL backups, and zero-downtime updates.

## 2. One-Time Administrator Initialization (`krish137u@gmail.com`)

1. On your server or local machine, copy `.env.example` to `.env` and restrict file permissions:
   ```bash
   cp .env.example .env
   chmod 600 .env
   ```
2. Set `FIRST_ADMIN_EMAIL=krish137u@gmail.com` and replace `FIRST_ADMIN_PASSWORD` with a newly generated strong password in `.env`.
3. Run the migration and bootstrap script:
   ```bash
   python -m migrations.run_migrations
   ```
4. Once initialized, remove `FIRST_ADMIN_PASSWORD` from `.env`.

## 3. Local Development on Windows (VS Code)

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
python -m migrations.run_migrations
uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000
```

## 4. Production Deployment on Linux VPS (PostgreSQL + Nginx + HTTPS)

```bash
sudo apt update && sudo apt install -y python3-venv python3-pip postgresql nginx certbot python3-certbot-nginx
sudo -u postgres psql -c "CREATE USER blockhub_user WITH PASSWORD 'STRONG_DB_PASSWORD';"
sudo -u postgres psql -c "CREATE DATABASE blockhub_db OWNER blockhub_user;"

# Deploy to /opt/blockhub, configure /opt/blockhub/.env, and initialize schema
/opt/blockhub/.venv/bin/python -m migrations.run_migrations

# Enable systemd service, Nginx reverse proxy, Let's Encrypt SSL, and daily DB backups
sudo cp deploy/blockhub.service /etc/systemd/system/blockhub.service
sudo systemctl daemon-reload && sudo systemctl enable --now blockhub
sudo cp deploy/nginx_blockhub.conf /etc/nginx/sites-available/blockhub
sudo ln -sf /etc/nginx/sites-available/blockhub /etc/nginx/sites-enabled/blockhub
sudo certbot --nginx -d blockhub.example.com
sudo cp deploy/backup_db.sh /etc/cron.daily/blockhub-backup
sudo chmod +x /etc/cron.daily/blockhub-backup
```
