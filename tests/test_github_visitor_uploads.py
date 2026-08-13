"""Uploads a GitHub visitor would actually try after cloning and running this app."""

from __future__ import annotations

import re
from io import BytesIO
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from PIL import Image, ImageDraw

from app.main import app

client = TestClient(app)

MEDIA_BOX_RE = re.compile(rb"/MediaBox \[ 0 0 ([0-9.]+) ([0-9.]+) \]")

_OUTSIDE_TEMP_PROBES = (
    Path("/Users/alex/Desktop/scan.png"),
    Path("/etc/passwd.png"),
    Path("/tmp/scan.png"),
    Path("/tmp/passwd.png"),
    Path.cwd() / "scan.png",
    Path.cwd() / "passwd.png",
    Path.cwd() / "Users" / "alex" / "Desktop" / "scan.png",
    Path.cwd() / "etc" / "passwd.png",
)


def _png_bytes(
    size: tuple[int, int] = (48, 32),
    color: tuple[int, int, int] | tuple[int, int, int, int] = (190, 60, 45),
    *,
    mode: str = "RGB",
) -> bytes:
    buffer = BytesIO()
    Image.new(mode, size, color).save(buffer, format="PNG")
    return buffer.getvalue()


def _jpeg_bytes(
    size: tuple[int, int] = (48, 32),
    color: tuple[int, int, int] = (35, 95, 155),
    *,
    orientation: int | None = None,
) -> bytes:
    buffer = BytesIO()
    image = Image.new("RGB", size, color)
    kwargs: dict = {"format": "JPEG"}
    if orientation is not None:
        exif = image.getexif()
        exif[274] = orientation
        kwargs["exif"] = exif
    image.save(buffer, **kwargs)
    return buffer.getvalue()


def _convert(filename: str, data: bytes, content_type: str):
    return client.post("/api/convert", files={"file": (filename, data, content_type)})


def _assert_pdf_response(response) -> bytes:
    assert response.status_code == 200
    assert response.headers.get("content-type", "").startswith("application/pdf")
    body = response.content
    assert body.startswith(b"%PDF")
    return body


def test_windows_screenshot_filename_with_spaces_converts_to_pdf() -> None:
    response = _convert("My Photo.PNG", _png_bytes((72, 48), (48, 110, 200)), "image/png")
    _assert_pdf_response(response)


@pytest.mark.parametrize(
    ("filename", "payload", "content_type"),
    [
        ("foto_vacaciones.jpg", _jpeg_bytes((56, 40), (210, 140, 70)), "image/jpeg"),
        ("снимок.png", _png_bytes((56, 40), (70, 130, 90)), "image/png"),
    ],
)
def test_unicode_or_vacation_photo_filename_converts_to_pdf(
    filename: str, payload: bytes, content_type: str
) -> None:
    _assert_pdf_response(_convert(filename, payload, content_type))


def test_phone_jpeg_exif_orientation_6_pdf_page_is_portrait() -> None:
    payload = _jpeg_bytes((80, 40), (20, 70, 140), orientation=6)
    response = _convert("IMG_20260813_143022.jpg", payload, "image/jpeg")
    body = _assert_pdf_response(response)

    match = MEDIA_BOX_RE.search(body)
    assert match, body[:400]
    width, height = float(match.group(1)), float(match.group(2))
    assert height > width


def test_transparent_rgba_screenshot_converts_to_pdf() -> None:
    image = Image.new("RGBA", (64, 40), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    for y in range(0, 40, 8):
        for x in range(0, 64, 8):
            if ((x // 8) + (y // 8)) % 2 == 0:
                draw.rectangle((x, y, x + 7, y + 7), fill=(40, 140, 255, 165))
            else:
                draw.rectangle((x, y, x + 7, y + 7), fill=(255, 255, 255, 0))
    buffer = BytesIO()
    image.save(buffer, format="PNG")

    response = _convert("Screenshot 2026-08-13 093012.png", buffer.getvalue(), "image/png")
    body = _assert_pdf_response(response)
    assert body.startswith(b"%PDF")


@pytest.mark.parametrize(
    ("filename", "image_format", "content_type"),
    [
        ("holiday.webp", "WEBP", "image/webp"),
        ("Desktop_photo.bmp", "BMP", "image/bmp"),
        ("scan0001.tiff", "TIFF", "image/tiff"),
    ],
)
def test_homepage_listed_raster_format_converts_to_pdf(
    filename: str, image_format: str, content_type: str
) -> None:
    homepage = client.get("/")
    assert homepage.status_code == 200
    ext = "." + filename.rsplit(".", 1)[-1]
    assert ext in homepage.text

    buffer = BytesIO()
    Image.new("RGB", (36, 28), (90, 55, 160)).save(buffer, format=image_format)
    _assert_pdf_response(_convert(filename, buffer.getvalue(), content_type))


def test_real_pdf_with_leading_whitespace_passthrough() -> None:
    payload = (
        b"\r\n\r\n"
        b"%PDF-1.4\n"
        b"%\xe2\xe3\xcf\xd3\n"
        b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
        b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n"
        b"3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] >>\nendobj\n"
        b"xref\n0 4\n0000000000 65535 f \n"
        b"trailer\n<< /Size 4 /Root 1 0 R >>\n"
        b"startxref\n0\n%%EOF\n"
    )
    response = _convert("Quarterly Report.pdf", payload, "application/pdf")

    assert response.status_code == 200
    assert response.headers.get("content-type", "").startswith("application/pdf")
    assert re.match(rb"\s*%PDF-1.4", response.content)


def test_readme_markdown_upload_converts_to_pdf() -> None:
    readme = (
        "# anythingintopdfbot\n\n"
        "Clone the repo, install, and convert a screenshot to PDF.\n\n"
        "## Usage\n\n"
        "Open the homepage and upload a file.\n"
    ).encode("utf-8")
    _assert_pdf_response(_convert("README.md", readme, "text/markdown"))


def test_windows_crlf_utf8_bom_txt_converts_to_pdf() -> None:
    notes = (
        "Meeting notes from cloning anythingintopdfbot\r\n"
        "\r\n"
        "- Ran the app locally\r\n"
        "- Uploaded this Notepad file\r\n"
    ).encode("utf-8-sig")
    assert notes.startswith(b"\xef\xbb\xbf")
    assert b"\r\n" in notes

    _assert_pdf_response(_convert("New Text Document.txt", notes, "text/plain"))


@pytest.mark.parametrize(
    "filename",
    [
        r"..\..\Users\alex\Desktop\scan.png",
        "../../../etc/passwd.png",
    ],
)
def test_nested_looking_upload_name_stays_in_temp_and_does_not_500(filename: str) -> None:
    existed_before = {path: path.exists() for path in _OUTSIDE_TEMP_PROBES}

    response = _convert(filename, _png_bytes((24, 24), (110, 110, 110)), "image/png")

    assert response.status_code != 500
    assert response.status_code == 200 or 400 <= response.status_code < 500
    if response.status_code == 200:
        assert response.content.startswith(b"%PDF")
    else:
        assert not (response.content or b"").startswith(b"%PDF")

    for path in _OUTSIDE_TEMP_PROBES:
        if not existed_before[path]:
            assert not path.exists(), f"upload wrote outside temp: {path}"


def test_very_long_but_valid_filename_does_not_500() -> None:
    prefix = "Full_resolution_export_from_phone_gallery_"
    filename = prefix + ("n" * (180 - len(prefix))) + ".png"
    assert len(filename) == 184  # ~180 char stem + .png

    response = _convert(filename, _png_bytes((20, 16), (50, 50, 50)), "image/png")

    assert response.status_code != 500
    assert response.status_code == 200 or 400 <= response.status_code < 500
    if response.status_code == 200:
        assert response.content.startswith(b"%PDF")


def test_multipage_tiff_converts_to_pdf() -> None:
    page1 = Image.new("RGB", (28, 36), (170, 50, 50))
    page2 = Image.new("RGB", (28, 36), (40, 70, 160))
    buffer = BytesIO()
    page1.save(buffer, format="TIFF", save_all=True, append_images=[page2])

    response = _convert("scan_two_pages.tiff", buffer.getvalue(), "image/tiff")
    body = _assert_pdf_response(response)

    boxes = MEDIA_BOX_RE.findall(body)
    count_match = re.search(rb"/Count (\d+)", body)
    if count_match:
        assert int(count_match.group(1)) == 2
    elif boxes:
        assert len(boxes) == 2
