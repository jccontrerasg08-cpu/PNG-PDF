"""Everyday session: open the site, convert normal files, get named PDFs."""

from io import BytesIO
from urllib.parse import unquote
import re

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from app.main import app

client = TestClient(app)


def _png(size: tuple[int, int] = (800, 600), color: tuple[int, int, int] = (40, 90, 160)) -> bytes:
    buffer = BytesIO()
    Image.new("RGB", size, color).save(buffer, format="PNG")
    return buffer.getvalue()


def _jpeg(size: tuple[int, int] = (800, 600), color: tuple[int, int, int] = (200, 80, 50)) -> bytes:
    buffer = BytesIO()
    Image.new("RGB", size, color).save(buffer, format="JPEG")
    return buffer.getvalue()


def _download_name(response) -> str:
    """Filename a browser would save from Content-Disposition (including RFC 5987)."""

    header = response.headers.get("content-disposition", "")
    star = re.search(r"filename\*=utf-8''([^;]+)", header, re.I)
    if star:
        return unquote(star.group(1)).lower()
    quoted = re.search(r'filename="([^"]+)"', header, re.I)
    if quoted:
        return quoted.group(1).lower()
    plain = re.search(r"filename=([^;]+)", header, re.I)
    return (plain.group(1).strip() if plain else "").lower()


def _disposition(response) -> str:
    return response.headers.get("content-disposition", "").lower()


def test_homepage_explains_convert_and_no_persistence() -> None:
    html = client.get("/").text

    assert "Convert" in html
    assert "not persisted" in html.lower()


def test_file_picker_accept_matches_supported_types() -> None:
    html = client.get("/").text
    api = client.get("/api/supported-types").json()["extensions"]
    match = re.search(r"<input[^>]*name=\"file\"[^>]*>", html)

    assert match is not None
    tag = match.group(0)
    accept = re.search(r'accept="([^"]*)"', tag)
    assert accept is not None
    assert accept.group(1).split(",") == api


def test_iphone_jpg_downloads_as_named_pdf() -> None:
    response = client.post(
        "/api/convert",
        files={"file": ("IMG_1234.JPG", _jpeg(), "image/jpeg")},
    )

    assert response.status_code == 200
    assert response.content.startswith(b"%PDF")
    assert "attachment" in _disposition(response)
    assert _download_name(response) == "img_1234.pdf"


def test_macos_screenshot_png_converts() -> None:
    name = "Screenshot 2026-08-13 at 10.41.22 AM.png"
    response = client.post(
        "/api/convert",
        files={"file": (name, _png((640, 400)), "image/png")},
    )

    assert response.status_code == 200
    assert _download_name(response) == "screenshot 2026-08-13 at 10.41.22 am.pdf"


def test_windows_jpeg_extension_converts() -> None:
    response = client.post(
        "/api/convert",
        files={"file": ("Holiday.jpeg", _jpeg((320, 240)), "image/jpeg")},
    )

    assert response.status_code == 200
    assert _download_name(response) == "holiday.pdf"


def test_typical_photo_pdf_uses_96_dpi_page() -> None:
    response = client.post(
        "/api/convert",
        files={"file": ("photo.png", _png((800, 600)), "image/png")},
    )

    assert response.status_code == 200
    assert b"%%EOF" in response.content
    match = re.search(rb"/MediaBox \[ 0 0 ([0-9.]+) ([0-9.]+) \]", response.content)
    assert match
    assert float(match.group(1)) == pytest.approx(800 * 72 / 96)
    assert float(match.group(2)) == pytest.approx(600 * 72 / 96)


def test_existing_pdf_downloads_with_same_stem() -> None:
    payload = b"%PDF-1.4\n1 0 obj<<>>endobj\ntrailer<<>>\n%%EOF\n"
    response = client.post(
        "/api/convert",
        files={"file": ("Report.pdf", payload, "application/pdf")},
    )

    assert response.status_code == 200
    assert _download_name(response) == "report.pdf"


def test_notes_txt_downloads_as_notes_pdf() -> None:
    response = client.post(
        "/api/convert",
        files={"file": ("notes.txt", b"Buy milk\nCall Alex\n", "text/plain")},
    )

    assert response.status_code == 200
    assert _download_name(response) == "notes.pdf"


def test_one_sitting_png_jpg_pdf_txt_all_succeed() -> None:
    uploads = [
        ("a.png", _png((32, 32)), "image/png"),
        ("b.jpg", _jpeg((32, 32)), "image/jpeg"),
        ("c.pdf", b"%PDF-1.4\n%%EOF\n", "application/pdf"),
        ("d.txt", b"hello\n", "text/plain"),
    ]
    for name, data, content_type in uploads:
        response = client.post("/api/convert", files={"file": (name, data, content_type)})
        assert response.status_code == 200, name
        assert response.content.startswith(b"%PDF"), name
