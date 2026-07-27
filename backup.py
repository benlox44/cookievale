#!/usr/bin/env python3
import gzip
import logging
import shutil
import subprocess
import sys
from datetime import datetime
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


def load_env(env_file: Path) -> dict[str, str]:
    """Parse .env line by line to avoid shell interpretation of special chars."""
    env: dict[str, str] = {}
    if not env_file.exists():
        log.error("[ERROR] .env file not found: %s", env_file)
        sys.exit(1)
    for line in env_file.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if "=" not in stripped:
            continue
        key, _, value = stripped.partition("=")
        key = key.strip()
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in ('"', "'"):
            value = value[1:-1]
        env[key] = value
    return env


def _is_timestamp_dir(name: str) -> bool:
    if len(name) != 19 or "_" not in name:
        return False
    try:
        datetime.strptime(name, "%Y-%m-%d_%H%M%S")
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

    env = load_env(SCRIPT_DIR / ".env")

    backup_dest = env.get("BACKUP_DEST", "").strip()
    if not backup_dest:
        log.error("[ERROR] BACKUP_DEST missing in .env")
        sys.exit(1)

    dest = Path(backup_dest)
    dest.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    backup_dir = dest / timestamp
    config_dir = backup_dir / "config"
    media_dir = backup_dir / "media"
    config_dir.mkdir(parents=True, exist_ok=True)
    media_dir.mkdir(parents=True, exist_ok=True)

    log.info("[*] Destination: %s", backup_dir)

    # ---- Database dump (compressed) ----
    log.info("[*] Exporting database...")
    db_user = env.get("POSTGRES_USER", "cookie_user")
    db_name = env.get("POSTGRES_DB", "cookievale")
    dump_path = config_dir / "cookievale_db_dump.sql.gz"

    try:
        result = subprocess.run(
            [
                "docker", "compose", "exec", "-T", "db",
                "pg_dump", "-U", db_user, "-d", db_name,
            ],
            capture_output=True,
            timeout=300,
            cwd=str(SCRIPT_DIR),
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
        log.error("[ERROR] docker not found — is Docker installed?")
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
    media_root = env.get("MEDIA_ROOT", "").strip()
    if not media_root:
        log.warning("[WARNING] MEDIA_ROOT not declared, skipping media files")
    else:
        media_src = Path(media_root)
        if not media_src.exists():
            log.warning("[WARNING] MEDIA_ROOT (%s) does not exist, skipping", media_src)
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
        total_size, remaining, BACKUP_RETENTION,
    )


if __name__ == "__main__":
    main()
