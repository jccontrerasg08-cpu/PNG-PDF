from io import BytesIO

from fastapi.testclient import TestClient
from PIL import Image

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
