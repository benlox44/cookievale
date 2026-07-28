import logging
import os
import shutil
import uuid

from fastapi import UploadFile

logger = logging.getLogger(__name__)

ALLOWED_MIME_TYPES = {
    "image/jpeg",
    "image/png",
    "image/webp",
    "image/gif",
}

MIME_TO_EXT = {
    "image/jpeg": "jpg",
    "image/png": "png",
    "image/webp": "webp",
    "image/gif": "gif",
}

MAX_FILE_SIZE = 10 * 1024 * 1024


def validate_upload(file: UploadFile) -> bool:
    if not file.filename:
        return False

    content_type = file.content_type
    if content_type not in ALLOWED_MIME_TYPES:
        return False

    file.file.seek(0, 2)
    size = file.file.tell()
    file.file.seek(0)

    return not size > MAX_FILE_SIZE


def get_safe_extension(file: UploadFile) -> str:
    content_type = file.content_type or ""
    if content_type in MIME_TO_EXT:
        return MIME_TO_EXT[content_type]

    if file.filename:
        name = os.path.basename(file.filename)
        if "." in name:
            ext = name.rsplit(".", 1)[-1].lower()
            if ext in MIME_TO_EXT.values():
                return ext

    return "bin"


def save_uploads(
    files: list[UploadFile], target_dir: str, url_prefix: str
) -> list[str]:
    os.makedirs(target_dir, exist_ok=True)
    saved_urls: list[str] = []

    for file in files:
        if not validate_upload(file):
            logger.warning("Rejected invalid upload: %s", file.filename)
            continue

        ext = get_safe_extension(file)
        filename = f"{uuid.uuid4().hex}.{ext}"
        filepath = os.path.join(target_dir, filename)

        with open(filepath, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        saved_urls.append(f"{url_prefix}/{filename}")

    return saved_urls
