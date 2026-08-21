import json
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


def _detect_image_type(file: UploadFile) -> str | None:
    header = file.file.read(12)
    file.file.seek(0)

    if len(header) < 12:
        return None

    if header.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if header.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if header.startswith((b"GIF87a", b"GIF89a")):
        return "image/gif"
    if header[:4] == b"RIFF" and header[8:12] == b"WEBP":
        return "image/webp"

    return None


def validate_upload(file: UploadFile) -> bool:
    if not file.filename:
        return False

    content_type = file.content_type
    if content_type not in ALLOWED_MIME_TYPES:
        return False

    detected = _detect_image_type(file)
    if detected is None or detected != content_type:
        return False

    file.file.seek(0, 2)
    size = file.file.tell()
    file.file.seek(0)

    return not size > MAX_FILE_SIZE


def get_safe_extension(file: UploadFile) -> str:
    detected = _detect_image_type(file)
    if detected in MIME_TO_EXT:
        return MIME_TO_EXT[detected]

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


def build_image_order(
    image_order: str,
    current_urls: list[str],
    new_urls: list[str],
) -> list[str]:
    # image_order is a JSON list mixing existing URLs and "new:<index>"
    # placeholders that map to saved new photos (in file-submit order).
    try:
        tokens = json.loads(image_order)
    except (ValueError, TypeError):
        return []
    if not isinstance(tokens, list):
        return []

    valid_current = set(current_urls)
    ordered: list[str] = []
    for token in tokens:
        if not isinstance(token, str):
            continue
        if token.startswith("new:"):
            index_str = token[4:]
            if not index_str.isdigit():
                continue
            index = int(index_str)
            if 0 <= index < len(new_urls) and new_urls[index] not in ordered:
                ordered.append(new_urls[index])
        elif token in valid_current and token not in ordered:
            ordered.append(token)

    # Keep any new photo not referenced by the order (defensive).
    for url in new_urls:
        if url not in ordered:
            ordered.append(url)

    return ordered


def delete_media_files(media_dir: str, urls: list[str]) -> None:
    for url in urls:
        filename = os.path.basename(url)
        if not filename:
            continue
        filepath = os.path.join(media_dir, filename)
        if os.path.isfile(filepath):
            os.remove(filepath)


def update_photo_set(
    current_urls: list[str],
    existing_urls: list[str],
    image_order: str,
    photos: list[UploadFile] | None,
    max_images: int,
    media_dir: str,
    url_prefix: str,
) -> tuple[list[str], list[str]]:
    """Reconcile kept photos, new uploads and ordering into the final set.

    Shared by orders and products (identical edit-photo behavior): keeps the
    photos the form still references, saves new uploads up to max_images, and
    applies the drag-and-drop order. Returns (final_urls, removed_urls) so the
    caller can delete the media files that were dropped.
    """
    current_set = set(current_urls)
    kept = [url for url in existing_urls if url in current_set]

    new_urls: list[str] = []
    if photos:
        valid_photos = [p for p in photos if p.filename]
        if valid_photos:
            remaining = max_images - len(kept)
            if remaining > 0:
                new_urls = save_uploads(valid_photos[:remaining], media_dir, url_prefix)

    final_urls = build_image_order(image_order, current_urls, new_urls)
    if not final_urls:
        # Empty/malformed image_order: keep existing photos, then new.
        final_urls = kept + new_urls
    final_urls = final_urls[:max_images]

    removed = [url for url in current_urls if url not in final_urls]
    return final_urls, removed
