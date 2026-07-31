#!/usr/bin/env python3
import gzip
import logging
import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
BACKUP_RETENTION = 7
LOG_FILE = SCRIPT_DIR / "backup.log"

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger(__name__)


def _is_timestamp_dir(name: str) -> bool:
    # "%Y-%m-%d_%H%M%S" is 17 chars (4+1+2+1+2+1+6)
    if len(name) != 17 or "_" not in name:
        return False
    try:
        datetime.strptime(name, "%Y-%m-%d_%H%M%S").replace(tzinfo=timezone.utc)
        return True
    except ValueError:
        return False


def _format_size(size_bytes: int) -> str:
    for unit in ("B", "K", "M", "G", "T"):
        if size_bytes < 1024:
            return f"{size_bytes}{unit}"
        size_bytes //= 1024
    return f"{size_bytes}P"


def _dir_size(path: Path) -> int:
    return sum(f.stat().st_size for f in path.rglob("*") if f.is_file())


def main() -> None:
    log.info("=== CookieVale Backup Started ===")

    db_user = os.environ["POSTGRES_USER"]
    db_name = os.environ["POSTGRES_DB"]
    db_password = os.environ["POSTGRES_PASSWORD"]
    dest = Path(os.environ["CONTAINER_BACKUP_PATH"])
    media_root = os.environ["CONTAINER_MEDIA_PATH"]

    dest.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now(tz=timezone.utc).strftime("%Y-%m-%d_%H%M%S")
    backup_dir = dest / timestamp
    config_dir = backup_dir / "config"
    media_dir = backup_dir / "media"
    config_dir.mkdir(parents=True, exist_ok=True)
    media_dir.mkdir(parents=True, exist_ok=True)

    log.info("[*] Destination: %s", backup_dir)

    # ---- Database dump (compressed) ----
    log.info("[*] Exporting database...")
    dump_path = config_dir / "cookievale_db_dump.sql.gz"

    try:
        result = subprocess.run(
            ["pg_dump", "-h", "db", "-U", db_user, "-d", db_name],
            env={**os.environ, "PGPASSWORD": db_password},
            capture_output=True,
            timeout=300,
            check=False,
        )
        if result.returncode != 0:
            stderr = result.stderr.decode("utf-8", errors="replace").strip()
            log.error("[ERROR] pg_dump failed: %s", stderr)
            shutil.rmtree(backup_dir, ignore_errors=True)
            sys.exit(1)

        with gzip.open(dump_path, "wb") as f:
            f.write(result.stdout)

        dump_size = _format_size(dump_path.stat().st_size)
        log.info("[OK] Database dump: %s", dump_size)
    except subprocess.TimeoutExpired:
        log.error("[ERROR] pg_dump timed out after 5 minutes")
        shutil.rmtree(backup_dir, ignore_errors=True)
        sys.exit(1)
    except FileNotFoundError:
        log.error(
            "[ERROR] pg_dump not found — is postgresql-client installed in the web container?"
        )
        shutil.rmtree(backup_dir, ignore_errors=True)
        sys.exit(1)

    # ---- Verify dump ----
    if dump_path.stat().st_size == 0:
        log.error("[ERROR] Database dump is empty (0 bytes)")
        shutil.rmtree(backup_dir, ignore_errors=True)
        sys.exit(1)

    try:
        with gzip.open(dump_path, "rb") as f:
            f.read(1)
    except (gzip.BadGzipFile, OSError, EOFError) as e:
        log.error("[ERROR] Database dump corrupted: %s", e)
        shutil.rmtree(backup_dir, ignore_errors=True)
        sys.exit(1)

    log.info("[OK] Dump integrity verified")

    # ---- Copy .env ----
    log.info("[*] Copying .env...")
    shutil.copy2(SCRIPT_DIR / ".env", config_dir / ".env")

    # ---- Media sync ----
    media_src = Path(media_root)
    if not media_src.exists():
        log.warning(
            "[WARNING] CONTAINER_MEDIA_PATH (%s) does not exist, skipping", media_src
        )
    else:
        log.info("[*] Syncing media from %s...", media_src)
        if media_dir.exists():
            shutil.rmtree(media_dir, ignore_errors=True)
        shutil.copytree(media_src, media_dir, symlinks=True)
        media_size = _format_size(_dir_size(media_dir))
        log.info("[OK] Media synced: %s", media_size)

    # ---- Rotate old backups ----
    log.info("[*] Cleaning old backups (keeping last %d)...", BACKUP_RETENTION)
    backup_dirs = sorted(
        (d for d in dest.iterdir() if d.is_dir() and _is_timestamp_dir(d.name)),
        key=lambda d: d.stat().st_mtime,
        reverse=True,
    )
    for old_dir in backup_dirs[BACKUP_RETENTION:]:
        log.info("  Removing: %s", old_dir)
        shutil.rmtree(old_dir, ignore_errors=True)

    # ---- Summary ----
    total_size = _format_size(_dir_size(backup_dir))
    remaining = min(len(backup_dirs), BACKUP_RETENTION)
    log.info(
        "=== Backup Completed Successfully === (%s, %d/%d backups stored)",
        total_size,
        remaining,
        BACKUP_RETENTION,
    )


if __name__ == "__main__":
    main()
