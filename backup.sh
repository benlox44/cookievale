#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

LOG_FILE="$SCRIPT_DIR/backup.log"
BACKUP_RETENTION=7

log() {
    local msg="[$(date '+%Y-%m-%d %H:%M:%S')] $*"
    echo "$msg"
    echo "$msg" >> "$LOG_FILE"
}

load_env() {
    local env_file="$1"
    while IFS= read -r line || [ -n "$line" ]; do
        line="${line#"${line%%[![:space:]]*}"}"
        line="${line%"${line##*[![:space:]]}"}"
        [[ -z "$line" || "$line" == \#* ]] && continue
        if [[ "$line" =~ ^([A-Za-z_][A-Za-z0-9_]*)=(.*)$ ]]; then
            local key="${BASH_REMATCH[1]}"
            local value="${BASH_REMATCH[2]}"
            value="${value#\"}"; value="${value%\"}"
            value="${value#\'}"; value="${value%\'}"
            export "$key=$value"
        fi
    done < "$env_file"
}

log "=== CookieVale Backup Started ==="

# ---- Load .env ----
load_env ".env"

# ---- Validate destination ----
if [ -z "${BACKUP_DEST// /}" ]; then
    log "[ERROR] BACKUP_DEST missing in .env"
    exit 1
fi

mkdir -p "$BACKUP_DEST"

# ---- Timestamped folder ----
TIMESTAMP=$(date '+%Y-%m-%d_%H%M%S')
BACKUP_DIR="$BACKUP_DEST/$TIMESTAMP"
mkdir -p "$BACKUP_DIR/config"
mkdir -p "$BACKUP_DIR/media"

log "[*] Destination: $BACKUP_DIR"

# ---- Database dump (compressed) ----
log "[*] Exporting database..."
DB_USER="${POSTGRES_USER:-cookie_user}"
DB_NAME="${POSTGRES_DB:-cookievale}"
DUMP_FILE="$BACKUP_DIR/config/cookievale_db_dump.sql.gz"

if docker compose exec -T db pg_dump -U "$DB_USER" -d "$DB_NAME" | gzip > "$DUMP_FILE"; then
    DUMP_SIZE=$(du -h "$DUMP_FILE" | cut -f1)
    log "[OK] Database dump: $DUMP_SIZE"
else
    log "[ERROR] pg_dump failed"
    rm -rf "$BACKUP_DIR"
    exit 1
fi

# ---- Verify dump ----
if [ ! -s "$DUMP_FILE" ]; then
    log "[ERROR] Database dump is empty (0 bytes)"
    rm -rf "$BACKUP_DIR"
    exit 1
fi

if ! gzip -t "$DUMP_FILE" 2>/dev/null; then
    log "[ERROR] Database dump corrupted (gzip integrity check failed)"
    rm -rf "$BACKUP_DIR"
    exit 1
fi

log "[OK] Dump integrity verified"

# ---- Copy .env ----
log "[*] Copying .env..."
cp "$SCRIPT_DIR/.env" "$BACKUP_DIR/config/"

# ---- Media sync ----
if [ -z "${MEDIA_ROOT:-}" ]; then
    log "[WARNING] MEDIA_ROOT not declared, skipping media files"
else
    if [ -d "$MEDIA_ROOT" ]; then
        log "[*] Syncing media from $MEDIA_ROOT..."
        if command -v rsync &>/dev/null; then
            if rsync -a --delete "$MEDIA_ROOT/" "$BACKUP_DIR/media/" 2>> "$LOG_FILE"; then
                MEDIA_SIZE=$(du -sh "$BACKUP_DIR/media" 2>/dev/null | cut -f1)
                log "[OK] Media synced: $MEDIA_SIZE"
            else
                log "[WARNING] Media sync had errors (see $LOG_FILE)"
            fi
        else
            cp -a "$MEDIA_ROOT/." "$BACKUP_DIR/media/" 2>> "$LOG_FILE"
            MEDIA_SIZE=$(du -sh "$BACKUP_DIR/media" 2>/dev/null | cut -f1)
            log "[OK] Media copied (rsync not available): $MEDIA_SIZE"
        fi
    else
        log "[WARNING] MEDIA_ROOT ($MEDIA_ROOT) does not exist, skipping"
    fi
fi

# ---- Rotate old backups ----
log "[*] Cleaning old backups (keeping last $BACKUP_RETENTION)..."
BACKUP_COUNT=$(find "$BACKUP_DEST" -maxdepth 1 -type d -name '[0-9]*-[0-9]*_[0-9]*' 2>/dev/null | wc -l)
if [ "$BACKUP_COUNT" -gt "$BACKUP_RETENTION" ]; then
    find "$BACKUP_DEST" -maxdepth 1 -type d -name '[0-9]*-[0-9]*_[0-9]*' \
        -printf '%T@ %p\n' 2>/dev/null \
        | sort -rn \
        | tail -n +$((BACKUP_RETENTION + 1)) \
        | cut -d' ' -f2- \
        | while read -r old_dir; do
            log "  Removing: $old_dir"
            rm -rf "$old_dir"
        done
fi

# ---- Summary ----
TOTAL_SIZE=$(du -sh "$BACKUP_DIR" 2>/dev/null | cut -f1)
BACKUPS_ON_DISK=$(find "$BACKUP_DEST" -maxdepth 1 -type d -name '[0-9]*-[0-9]*_[0-9]*' 2>/dev/null | wc -l)
log "=== Backup Completed Successfully === ($TOTAL_SIZE, $BACKUPS_ON_DISK/$BACKUP_RETENTION backups stored)"
