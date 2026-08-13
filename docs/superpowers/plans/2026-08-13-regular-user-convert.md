# Regular-user convert flow Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Prove a normal GitHub visitor can convert everyday JPEG/PNG/PDF/TXT files and get a named PDF download; filter the file picker to those types.

**Architecture:** One new pytest module for the happy-path session. One Jinja `accept` attribute on the existing file input, fed from `supported_extensions` already passed to the template.

**Tech Stack:** FastAPI TestClient, Pillow, existing converters. No new dependencies.

## Global Constraints

- Python >= 3.10, Pillow already installed, pytest already installed
- Do not add HEIC/Office converters
- Do not edit `tests/test_github_visitor_mistakes.py`
- File picker `accept` must match `/api/supported-types` extensions
- Download filename is `{stem}.pdf` with `attachment`
- Image PDF default DPI is 96 when metadata is missing

---

### Task 1: Regular-user session tests

**Files:**
- Create: `tests/test_github_regular_user.py`
- Modify: `app/templates/index.html` (add `accept` after tests fail on it)

**Interfaces:**
- Consumes: `POST /api/convert`, `GET /`, `GET /api/supported-types`, `ImageToPdfConverter` 96 DPI default
- Produces: passing happy-path tests; file input `accept` attribute

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_github_regular_user.py
from io import BytesIO
import re
from fastapi.testclient import TestClient
from PIL import Image
from app.main import app

client = TestClient(app)

def _png(size=(800, 600), color=(40, 90, 160)):
    buf = BytesIO()
    Image.new("RGB", size, color).save(buf, format="PNG")
    return buf.getvalue()

def _jpeg(size=(800, 600), color=(200, 80, 50)):
    buf = BytesIO()
    Image.new("RGB", size, color).save(buf, format="JPEG")
    return buf.getvalue()

def test_homepage_explains_convert_and_no_persistence():
    html = client.get("/").text
    assert "Convert" in html
    assert "not persisted" in html.lower()

def test_file_picker_accept_matches_supported_types():
    html = client.get("/").text
    api = client.get("/api/supported-types").json()["extensions"]
    match = re.search(r'<input[^>]*name="file"[^>]*>', html)
    assert match
    tag = match.group(0)
    assert "accept=" in tag
    listed = re.search(r'accept="([^"]*)"', tag).group(1).split(",")
    assert listed == api

def test_iphone_jpg_downloads_as_named_pdf():
    response = client.post("/api/convert", files={"file": ("IMG_1234.JPG", _jpeg(), "image/jpeg")})
    assert response.status_code == 200
    assert response.content.startswith(b"%PDF")
    disp = response.headers.get("content-disposition", "").lower()
    assert "attachment" in disp
    assert "img_1234.pdf" in disp

def test_macos_screenshot_png_converts():
    name = "Screenshot 2026-08-13 at 10.41.22 AM.png"
    response = client.post("/api/convert", files={"file": (name, _png((640, 400)), "image/png")})
    assert response.status_code == 200
    assert "screenshot 2026-08-13 at 10.41.22 am.pdf" in response.headers.get("content-disposition", "").lower()

def test_windows_jpeg_extension_converts():
    response = client.post("/api/convert", files={"file": ("Holiday.jpeg", _jpeg((320, 240)), "image/jpeg")})
    assert response.status_code == 200
    assert "holiday.pdf" in response.headers.get("content-disposition", "").lower()

def test_typical_photo_pdf_uses_96_dpi_page():
    response = client.post("/api/convert", files={"file": ("photo.png", _png((800, 600)), "image/png")})
    assert response.status_code == 200
    assert b"%%EOF" in response.content
    match = re.search(rb"/MediaBox \[ 0 0 ([0-9.]+) ([0-9.]+) \]", response.content)
    assert match
    assert float(match.group(1)) == pytest.approx(800 * 72 / 96)
    assert float(match.group(2)) == pytest.approx(600 * 72 / 96)

def test_existing_pdf_downloads_with_same_stem():
    payload = b"%PDF-1.4\n1 0 obj<<>>endobj\ntrailer<<>>\n%%EOF\n"
    response = client.post("/api/convert", files={"file": ("Report.pdf", payload, "application/pdf")})
    assert response.status_code == 200
    assert "report.pdf" in response.headers.get("content-disposition", "").lower()

def test_notes_txt_downloads_as_notes_pdf():
    response = client.post("/api/convert", files={"file": ("notes.txt", b"Buy milk\nCall Alex\n", "text/plain")})
    assert response.status_code == 200
    assert "notes.pdf" in response.headers.get("content-disposition", "").lower()

def test_one_sitting_png_jpg_pdf_txt_all_succeed():
    files = [
        ("a.png", _png((32, 32)), "image/png"),
        ("b.jpg", _jpeg((32, 32)), "image/jpeg"),
        ("c.pdf", b"%PDF-1.4\n%%EOF\n", "application/pdf"),
        ("d.txt", b"hello\n", "text/plain"),
    ]
    for name, data, ctype in files:
        response = client.post("/api/convert", files={"file": (name, data, ctype)})
        assert response.status_code == 200
        assert response.content.startswith(b"%PDF")
```

Need `import pytest` for approx.

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/test_github_regular_user.py -v --tb=short`  
Expected: `test_file_picker_accept_matches_supported_types` FAIL (no `accept=`). Filename tests may already pass.

- [ ] **Step 3: Add accept to the file input**

```html
<input id="file" name="file" type="file" required accept="{{ supported_extensions|join(',') }}" />
```

- [ ] **Step 4: Run tests and make sure they pass**

Run: `python3 -m pytest tests/test_github_regular_user.py tests/test_github_visitor_ui.py -v`  
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tests/test_github_regular_user.py app/templates/index.html docs/superpowers/specs/2026-08-13-regular-user-convert-design.md docs/superpowers/plans/2026-08-13-regular-user-convert.md
git commit -m "Test the everyday convert session a GitHub visitor would actually run."
```
