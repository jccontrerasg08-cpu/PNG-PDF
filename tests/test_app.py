from io import BytesIO

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from app.config import settings
from app.main import app


client = TestClient(app)


def test_health_and_readiness_endpoints() -> None:
    assert client.get("/healthz").json() == {"status": "ok"}
    assert client.get("/readyz").json() == {"status": "ready"}


def test_supported_types_contains_primary_formats() -> None:
    response = client.get("/api/supported-types")
    assert response.status_code == 200
    extensions = response.json()["extensions"]
    assert ".png" in extensions
    assert ".pdf" in extensions
    assert ".txt" in extensions


def test_png_upload_converts_to_pdf() -> None:
    buffer = BytesIO()
    Image.new("RGB", (32, 32), "red").save(buffer, format="PNG")
    buffer.seek(0)

    response = client.post(
        "/api/convert",
        files={"file": ("sample.png", buffer, "image/png")},
    )

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert response.content.startswith(b"%PDF")


def test_unsupported_upload_returns_415() -> None:
    response = client.post(
        "/api/convert",
        files={"file": ("sample.exe", b"nope", "application/octet-stream")},
    )

    assert response.status_code == 415


def test_dotfile_named_upload_is_still_recognized() -> None:
    buffer = BytesIO()
    Image.new("RGB", (16, 16), "blue").save(buffer, format="PNG")
    buffer.seek(0)

    response = client.post(
        "/api/convert",
        files={"file": (".png", buffer, "image/png")},
    )

    assert response.status_code == 200
    assert response.content.startswith(b"%PDF")


def test_truncated_image_returns_422_not_500() -> None:
    buffer = BytesIO()
    Image.new("RGB", (64, 64), "green").save(buffer, format="PNG")
    truncated = buffer.getvalue()[: len(buffer.getvalue()) // 2]

    response = client.post(
        "/api/convert",
        files={"file": ("broken.png", truncated, "image/png")},
    )

    assert response.status_code == 422


def test_oversized_upload_returns_413(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "max_upload_size_bytes", 10)

    response = client.post(
        "/api/convert",
        files={"file": ("big.txt", b"x" * 1000, "text/plain")},
    )

    assert response.status_code == 413


def test_allowed_extensions_setting_actually_restricts_uploads(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "allowed_extensions", {".pdf"})

    response = client.get("/api/supported-types")
    assert response.json()["extensions"] == [".pdf"]

    buffer = BytesIO()
    Image.new("RGB", (8, 8), "red").save(buffer, format="PNG")
    buffer.seek(0)

    response = client.post(
        "/api/convert",
        files={"file": ("sample.png", buffer, "image/png")},
    )
    assert response.status_code == 415


def test_jpeg_upload_converts_to_pdf() -> None:
    buffer = BytesIO()
    Image.new("RGB", (24, 24), "green").save(buffer, format="JPEG")
    buffer.seek(0)

    response = client.post(
        "/api/convert",
        files={"file": ("photo.jpg", buffer, "image/jpeg")},
    )

    assert response.status_code == 200
    assert response.content.startswith(b"%PDF")


def test_txt_upload_converts_to_pdf() -> None:
    response = client.post(
        "/api/convert",
        files={"file": ("note.txt", b"hello world\n", "text/plain")},
    )

    assert response.status_code == 200
    assert response.content.startswith(b"%PDF")


def test_pdf_upload_passthrough() -> None:
    payload = b"%PDF-1.4\n1 0 obj<<>>endobj\ntrailer<<>>\n%%EOF\n"
    response = client.post(
        "/api/convert",
        files={"file": ("doc.pdf", payload, "application/pdf")},
    )

    assert response.status_code == 200
    assert response.content.startswith(b"%PDF")


def test_garbage_pdf_upload_returns_422() -> None:
    response = client.post(
        "/api/convert",
        files={"file": ("fake.pdf", b"not a pdf", "application/pdf")},
    )

    assert response.status_code == 422
