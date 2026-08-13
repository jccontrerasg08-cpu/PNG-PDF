"""API reactions to clumsy GitHub-visitor uploads (wrong type, empty, lying names)."""

from io import BytesIO

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from app.converters.documents import TextDocumentToPdfConverter
from app.main import app

client = TestClient(app)


def _png_bytes(size: tuple[int, int] = (8, 8)) -> bytes:
    buffer = BytesIO()
    Image.new("RGB", size, "red").save(buffer, format="PNG")
    return buffer.getvalue()


def _jpeg_bytes(size: tuple[int, int] = (64, 64)) -> bytes:
    buffer = BytesIO()
    Image.new("RGB", size, "blue").save(buffer, format="JPEG")
    return buffer.getvalue()


def _post_file(
    filename: str,
    content: bytes,
    content_type: str = "application/octet-stream",
):
    return client.post(
        "/api/convert",
        files={"file": (filename, content, content_type)},
    )


def test_empty_png_returns_422_not_500() -> None:
    response = _post_file("empty.png", b"", "image/png")

    assert response.status_code == 422


def test_empty_pdf_returns_422_not_500() -> None:
    response = _post_file("empty.pdf", b"", "application/pdf")

    assert response.status_code == 422


@pytest.mark.parametrize("filename", ["report.docx", "sheet.xlsx", "slides.pptx"])
def test_corrupt_office_document_returns_422_not_500(filename: str) -> None:
    response = _post_file(
        filename,
        b"PK\x03\x04not-really-office",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )

    assert response.status_code == 422


def test_corrupt_iphone_heic_returns_422() -> None:
    response = _post_file("IMG_0001.heic", b"\x00\x00\x00\x18ftypheic", "image/heic")

    assert response.status_code == 422


def test_truncated_gif_returns_422() -> None:
    response = _post_file("funny.gif", b"GIF89a", "image/gif")

    assert response.status_code == 422


def test_garbage_svg_returns_422() -> None:
    response = _post_file("icon.svg", b"not-an-svg", "image/svg+xml")

    assert response.status_code == 422


def test_heic_from_non_heic_bytes_returns_422() -> None:
    response = _post_file("IMG_0001.heic", b"this is a jpeg joke not heic", "image/heic")

    assert response.status_code == 422


def test_jpeg_bytes_named_heic_returns_422() -> None:
    response = _post_file("IMG_0001.heic", _jpeg_bytes(), "image/heic")

    assert response.status_code == 422


def test_double_extension_pdf_exe_returns_415() -> None:
    response = _post_file("invoice.pdf.exe", b"MZ-not-an-exe", "application/octet-stream")

    assert response.status_code == 415


def test_png_bytes_named_txt_returns_422() -> None:
    response = _post_file("notes.txt", _png_bytes(), "text/plain")

    assert response.status_code == 422


def test_jpeg_bytes_named_pdf_returns_422() -> None:
    jpeg = _jpeg_bytes()
    assert b"%PDF-" not in jpeg[:1024]

    response = _post_file("file.pdf", jpeg, "application/pdf")

    assert response.status_code == 422


def test_png_content_type_with_exe_filename_returns_415() -> None:
    response = _post_file("file.exe", _png_bytes(), "image/png")

    assert response.status_code == 415


def test_wrong_form_field_name_upload_returns_4xx_not_500() -> None:
    response = client.post(
        "/api/convert",
        files={"upload": ("photo.png", _png_bytes(), "image/png")},
    )

    assert 400 <= response.status_code < 500


def test_one_by_one_png_still_converts() -> None:
    response = _post_file("tiny.png", _png_bytes((1, 1)), "image/png")

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert response.content.startswith(b"%PDF")


def test_text_over_max_pages_returns_422(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(TextDocumentToPdfConverter, "max_pages", 1)
    payload = ("line\n" * 80).encode("utf-8")

    response = _post_file("long.txt", payload, "text/plain")

    assert response.status_code == 422
    assert "too many pages" in response.json()["detail"].lower()


def test_latin1_txt_returns_422() -> None:
    response = _post_file("latin1.txt", "café".encode("latin-1"), "text/plain")

    assert response.status_code == 422


def test_missing_filename_returns_4xx_not_500() -> None:
    response = _post_file("", b"hello\n", "text/plain")

    assert 400 <= response.status_code < 500


def test_truncated_jpeg_returns_422_not_500() -> None:
    jpeg = _jpeg_bytes((64, 64))
    truncated = jpeg[: len(jpeg) // 2]

    response = _post_file("broken.jpg", truncated, "image/jpeg")

    assert response.status_code == 422
