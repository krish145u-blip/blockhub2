#!/usr/bin/env bash
# BLOCKHUB Production Update & Migration Runner
set -euo pipefail

APP_DIR="/opt/blockhub"
cd "$APP_DIR"

git pull origin main
"$APP_DIR/.venv/bin/pip" install --upgrade -r requirements.txt
"$APP_DIR/.venv/bin/python" -m migrations.run_migrations
sudo systemctl restart blockhub
sudo systemctl status blockhub --no-pager
