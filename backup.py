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
BACKUP_RETENTION = 2
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
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, _, value = stripped.partition("=")
        key = key.strip()
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in ('"', "'"):
            value = value[1:-1]
        env[key] = value
    return env


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


def _verify_backup_destination(dest: Path) -> bool:
    try:
        dest.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        log.error(
            "[ERROR] Backup destination %s is not accessible: %s. "
            "Check that BACKUP_DEST points to an available folder. "
            "No backup was created.",
            dest,
            exc,
        )
        return False

    probe = dest / ".backup_probe"
    try:
        probe.write_text("ok", encoding="utf-8")
        probe.unlink()
    except OSError as exc:
        log.error(
            "[ERROR] Backup destination %s is not writable: %s. No backup was created.",
            dest,
            exc,
        )
        return False

    return True


def _get_docker_compose_cmd() -> list[str]:
    if shutil.which("docker"):
        return ["docker", "compose"]
    if shutil.which("docker-compose"):
        return ["docker-compose"]
    log.error("[ERROR] docker command not found — is Docker installed?")
    sys.exit(1)


def main() -> None:
    log.info("=== CookieVale Backup Started ===")

    env = {**load_env(SCRIPT_DIR / ".env"), **os.environ}

    db_user = env.get("POSTGRES_USER", "")
    db_name = env.get("POSTGRES_DB", "")
    db_password = env.get("POSTGRES_PASSWORD", "")
    backup_dest = env.get("BACKUP_DEST", "").strip()
    media_root = env.get("MEDIA_ROOT", "").strip()

    if not db_user or not db_name:
        log.error("[ERROR] POSTGRES_USER and POSTGRES_DB must be declared in .env")
        sys.exit(1)

    if not backup_dest:
        log.error("[ERROR] BACKUP_DEST missing in .env")
        sys.exit(1)

    dest = Path(backup_dest)
    if not _verify_backup_destination(dest):
        sys.exit(1)

    timestamp = datetime.now(tz=timezone.utc).strftime("%Y-%m-%d_%H%M%S")
    backup_dir = dest / timestamp
    config_dir = backup_dir / "config"
    media_dir = backup_dir / "media"
    config_dir.mkdir(parents=True, exist_ok=True)
    media_dir.mkdir(parents=True, exist_ok=True)

    log.info("[*] Destination: %s", backup_dir)

    log.info("[*] Exporting database...")
    dump_path = config_dir / "cookievale_db_dump.sql.gz"

    compose_cmd = _get_docker_compose_cmd()
    cmd = [*compose_cmd, "exec", "-T"]
    if db_password:
        cmd.extend(["-e", f"PGPASSWORD={db_password}"])
    cmd.extend(["db", "pg_dump", "-U", db_user, "-d", db_name])

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            timeout=300,
            cwd=str(SCRIPT_DIR),
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
        log.error("[ERROR] docker command failed — is Docker installed and in PATH?")
        shutil.rmtree(backup_dir, ignore_errors=True)
        sys.exit(1)

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

    log.info("[*] Copying .env...")
    env_src = SCRIPT_DIR / ".env"
    with env_src.open("r", encoding="utf-8") as f:
        env_content = f.read()
    with (config_dir / ".env").open("w", encoding="utf-8", newline="\n") as f:
        f.write(env_content)

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
            shutil.copytree(media_src, media_dir, dirs_exist_ok=True)
            media_size = _format_size(_dir_size(media_dir))
            log.info("[OK] Media synced: %s", media_size)

    log.info("[*] Cleaning old backups (keeping last %d)...", BACKUP_RETENTION)
    backup_dirs = sorted(
        (d for d in dest.iterdir() if d.is_dir() and _is_timestamp_dir(d.name)),
        key=lambda d: d.stat().st_mtime,
        reverse=True,
    )
    for old_dir in backup_dirs[BACKUP_RETENTION:]:
        log.info("  Removing: %s", old_dir)
        shutil.rmtree(old_dir, ignore_errors=True)

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
