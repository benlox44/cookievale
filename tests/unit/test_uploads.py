import io

import pytest
from fastapi import UploadFile

from app.core import uploads

JPEG_MAGIC = b"\xff\xd8\xff\xe0"
PNG_MAGIC = b"\x89PNG\r\n\x1a\n"
GIF_MAGIC = b"GIF89a"
WEBP_MAGIC = b"RIFF\x00\x00\x00\x00WEBPVP8 "


def make_upload(
    content: bytes,
    name: str = "foto.jpg",
    mime: str = "image/jpeg",
) -> UploadFile:
    return UploadFile(
        filename=name, file=io.BytesIO(content), headers={"content-type": mime}
    )


def test_validate_accepts_known_image_types() -> None:
    assert uploads.validate_upload(make_upload(JPEG_MAGIC + b"\x00" * 32))
    assert uploads.validate_upload(
        make_upload(PNG_MAGIC + b"\x00" * 32, name="foto.png", mime="image/png")
    )
    assert uploads.validate_upload(
        make_upload(GIF_MAGIC + b"\x00" * 32, name="foto.gif", mime="image/gif")
    )
    assert uploads.validate_upload(
        make_upload(WEBP_MAGIC + b"\x00" * 32, name="foto.webp", mime="image/webp")
    )


def test_validate_rejects_mime_mismatch() -> None:
    assert not uploads.validate_upload(
        make_upload(JPEG_MAGIC + b"\x00" * 32, mime="image/png")
    )


def test_validate_rejects_unknown_mime() -> None:
    assert not uploads.validate_upload(
        make_upload(b"plain text bytes here", name="f.txt", mime="text/plain")
    )


def test_validate_rejects_empty_filename() -> None:
    assert not uploads.validate_upload(make_upload(JPEG_MAGIC + b"\x00" * 32, name=""))


def test_validate_rejects_oversized(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(uploads, "MAX_FILE_SIZE", 16)
    assert not uploads.validate_upload(make_upload(JPEG_MAGIC + b"\x00" * 64))


def test_get_safe_extension_from_magic() -> None:
    assert uploads.get_safe_extension(make_upload(JPEG_MAGIC + b"\x00" * 32)) == "jpg"
    assert (
        uploads.get_safe_extension(
            make_upload(GIF_MAGIC + b"\x00" * 32, name="f", mime="image/gif")
        )
        == "gif"
    )


def test_get_safe_extension_falls_back_to_filename() -> None:
    unknown = b"\x00\x01\x02\x03\x04\x05\x06\x07\x08\x09\x0a\x0b"
    upload = make_upload(unknown, name="foto.PNG", mime="image/jpeg")
    assert uploads.get_safe_extension(upload) == "png"


def test_get_safe_extension_defaults_to_bin() -> None:
    unknown = b"\x00\x01\x02\x03\x04\x05\x06\x07\x08\x09\x0a\x0b"
    assert uploads.get_safe_extension(make_upload(unknown, name="foto")) == "bin"


def test_build_image_order_mixes_existing_and_new() -> None:
    current = ["/media/a.jpg", "/media/b.jpg"]
    new = ["/media/n0.jpg", "/media/n1.jpg"]
    order = uploads.build_image_order('["/media/a.jpg","new:1","new:0"]', current, new)
    assert order == ["/media/a.jpg", "/media/n1.jpg", "/media/n0.jpg"]


def test_build_image_order_skips_invalid_tokens() -> None:
    current = ["/media/a.jpg"]
    new = ["/media/n0.jpg"]
    order = uploads.build_image_order(
        '["/media/missing.jpg","new:9","new:-1","new:0"]', current, new
    )
    assert order == ["/media/n0.jpg"]


def test_build_image_order_dedupes() -> None:
    current = ["/media/a.jpg"]
    new = ["/media/n0.jpg"]
    order = uploads.build_image_order(
        '["/media/a.jpg","new:0","/media/a.jpg"]', current, new
    )
    assert order == ["/media/a.jpg", "/media/n0.jpg"]


def test_build_image_order_appends_unreferenced_new() -> None:
    current = ["/media/a.jpg"]
    new = ["/media/n0.jpg", "/media/n1.jpg"]
    order = uploads.build_image_order("[]", current, new)
    assert order == ["/media/n0.jpg", "/media/n1.jpg"]


def test_update_photo_set_removes_dropped_photos(tmp_path) -> None:
    media_dir = str(tmp_path)
    current = ["/media/a.jpg", "/media/b.jpg"]
    final, removed = uploads.update_photo_set(
        current_urls=current,
        existing_urls=current,
        image_order='["/media/a.jpg"]',
        photos=None,
        max_images=8,
        media_dir=media_dir,
        url_prefix="/media",
    )
    assert final == ["/media/a.jpg"]
    assert removed == ["/media/b.jpg"]


def test_update_photo_set_saves_new_and_caps(
    tmp_path,
) -> None:
    media_dir = str(tmp_path)
    photos = [
        make_upload(JPEG_MAGIC + b"\x00" * 32, name=f"p{i}.jpg") for i in range(3)
    ]
    final, removed = uploads.update_photo_set(
        current_urls=[],
        existing_urls=[],
        image_order="[]",
        photos=photos,
        max_images=2,
        media_dir=media_dir,
        url_prefix="/media",
    )
    assert len(final) == 2
    assert removed == []
    assert len(list(tmp_path.iterdir())) == 2
