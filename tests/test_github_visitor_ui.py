from io import BytesIO
from re import DOTALL, findall, search

from fastapi.testclient import TestClient
from PIL import Image

from app.main import app

client = TestClient(app)


def _tiny_png() -> BytesIO:
    buffer = BytesIO()
    Image.new("RGB", (4, 4), "red").save(buffer, format="PNG")
    buffer.seek(0)
    return buffer


def test_homepage_returns_html_with_convert_form() -> None:
    response = client.get("/")

    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    html = response.text
    assert "<h1>Convert images and documents to PDF</h1>" in html
    assert 'action="/api/convert"' in html
    assert 'method="post"' in html.lower()
    assert 'enctype="multipart/form-data"' in html
    assert 'name="file"' in html
    assert 'type="file"' in html


def test_homepage_lists_same_extensions_as_supported_types_api() -> None:
    html = client.get("/").text
    listed = findall(r"<li>([^<]+)</li>", search(r'<ul class="extensions">(.*?)</ul>', html, DOTALL).group(1))
    api_extensions = client.get("/api/supported-types").json()["extensions"]

    assert listed == api_extensions


def test_homepage_stylesheet_is_served() -> None:
    response = client.get("/static/styles.css")

    assert response.status_code == 200
    assert "text/css" in response.headers["content-type"]
    assert "body" in response.text


def test_html_form_png_submit_downloads_pdf() -> None:
    response = client.post("/api/convert", files={"file": ("photo.png", _tiny_png(), "image/png")})

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert response.content.startswith(b"%PDF")
    assert ".pdf" in response.headers.get("content-disposition", "").lower()


def test_consecutive_form_conversions_both_succeed() -> None:
    for _ in range(2):
        response = client.post("/api/convert", files={"file": ("scan.png", _tiny_png(), "image/png")})
        assert response.status_code == 200
        assert response.content.startswith(b"%PDF")


def test_get_convert_is_method_not_allowed() -> None:
    response = client.get("/api/convert")

    assert 400 <= response.status_code < 500


def test_convert_without_file_field_returns_client_error() -> None:
    response = client.post("/api/convert")

    assert 400 <= response.status_code < 500


def test_homepage_has_viewport_meta_and_english_lang() -> None:
    html = client.get("/").text

    assert 'lang="en"' in html
    assert 'name="viewport"' in html
    assert "width=device-width" in html
