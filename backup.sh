#!/usr/bin/env bash
set -euo pipefail

echo "=== CookieVale Backup Started ==="

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

set -a
source .env
set +a

if [ -z "${BACKUP_DEST:-}" ]; then
    echo "[ERROR] BACKUP_DEST missing in .env"
    exit 1
fi

if [ ! -d "$BACKUP_DEST" ]; then
    echo "[ERROR] Destination $BACKUP_DEST does not exist"
    exit 1
fi

echo "[*] Exporting CookieVale Database..."
docker compose exec -T db pg_dump -U "${POSTGRES_USER:-cookie_user}" -d "${POSTGRES_DB:-cookievale}" > "$SCRIPT_DIR/cookievale_db_dump.sql"

echo "[*] Saving SQL dump and .env to backup destination..."
mkdir -p "$BACKUP_DEST/config"
cp "$SCRIPT_DIR/cookievale_db_dump.sql" "$BACKUP_DEST/config/"
cp "$SCRIPT_DIR/.env" "$BACKUP_DEST/config/"

echo "[*] Cleaning up local SQL dump..."
rm -f "$SCRIPT_DIR/cookievale_db_dump.sql"

if [ -z "${MEDIA_ROOT:-}" ]; then
    echo "[WARNING] MEDIA_ROOT is not declared, skipping media files."
else
    echo "[*] Syncing media from $MEDIA_ROOT to backup destination..."
    mkdir -p "$BACKUP_DEST/media"
    rsync -a --delete "$MEDIA_ROOT/" "$BACKUP_DEST/media/"
fi

echo "=== Backup Completed Successfully ==="
