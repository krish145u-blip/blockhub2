#!/usr/bin/env bash
# BLOCKHUB Automated PostgreSQL Backup Script (14-Day Retention)
# Install via: sudo cp deploy/backup_db.sh /etc/cron.daily/blockhub-backup && sudo chmod +x /etc/cron.daily/blockhub-backup
set -euo pipefail

BACKUP_DIR="/var/backups/blockhub"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
DB_NAME="${POSTGRES_DB:-blockhub_db}"
DB_USER="${POSTGRES_USER:-blockhub_user}"

mkdir -p "$BACKUP_DIR"
chmod 700 "$BACKUP_DIR"

pg_dump -U "$DB_USER" -h 127.0.0.1 -Fc "$DB_NAME" > "$BACKUP_DIR/blockhub_${TIMESTAMP}.dump"
find "$BACKUP_DIR" -type f -name "blockhub_*.dump" -mtime +14 -delete
echo "[BLOCKHUB] Backup completed: $BACKUP_DIR/blockhub_${TIMESTAMP}.dump"
