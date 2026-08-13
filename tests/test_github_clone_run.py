"""Checks a GitHub clone would see: README commands, packaging, health, convert, OpenAPI.

File reads plus FastAPI TestClient only — no network to GitHub.
"""

from __future__ import annotations

import json
import re
import tomllib
from io import BytesIO
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from app.main import app

ROOT = Path(__file__).resolve().parents[1]
CORE_LIBS = ("fastapi", "gunicorn", "pillow", "uvicorn")

client = TestClient(app)


def _tiny_png() -> bytes:
    buffer = BytesIO()
    Image.new("RGB", (8, 8), (200, 40, 40)).save(buffer, format="PNG")
    return buffer.getvalue()


def _distribution_name(spec: str) -> str:
    spec = spec.strip()
    if not spec or spec.startswith("#"):
        return ""
    spec = spec.split(";", 1)[0].strip()
    for sep in ("===", "==", ">=", "<=", "~=", "!=", ">", "<"):
        if sep in spec:
            spec = spec.split(sep, 1)[0]
            break
    return spec.split("[", 1)[0].strip().lower()


def _names_from_requirements(text: str) -> set[str]:
    names: set[str] = set()
    for line in text.splitlines():
        name = _distribution_name(line)
        if name:
            names.add(name)
    return names


def _procfile_web_command(text: str) -> str:
    for line in text.splitlines():
        if line.startswith("web:"):
            return line.split(":", 1)[1].strip()
    raise AssertionError("Procfile has no web: command")


def _dockerfile_cmd_tokens(text: str) -> list[str]:
    match = re.search(r"^CMD\s+(\[.*\])\s*$", text, re.MULTILINE)
    if match is None:
        raise AssertionError("Dockerfile has no JSON-array CMD")
    tokens = json.loads(match.group(1))
    assert isinstance(tokens, list) and tokens
    return [str(token) for token in tokens]


def test_readme_documents_clone_commands() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "pip install -e" in readme or "pip install" in readme
    assert "uvicorn app.main:app" in readme
    assert "python -m app" in readme
    assert "pytest" in readme


def test_procfile_web_matches_dockerfile_cmd_style() -> None:
    web = _procfile_web_command((ROOT / "Procfile").read_text(encoding="utf-8"))
    cmd = _dockerfile_cmd_tokens((ROOT / "Dockerfile").read_text(encoding="utf-8"))
    cmd_joined = " ".join(cmd)

    assert cmd[0] == "gunicorn"
    assert web.split()[0] == "gunicorn"
    assert "app.main:app" in cmd and "app.main:app" in web
    assert "uvicorn.workers.UvicornWorker" in cmd and "uvicorn.workers.UvicornWorker" in web
    assert "UvicornWorker" in cmd_joined


def test_pyproject_name_and_app_packages() -> None:
    data = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    assert data["project"]["name"] == "anythingintopdfbot"
    includes = data["tool"]["setuptools"]["packages"]["find"]["include"]
    assert "app*" in includes


def test_healthz_and_readyz_after_boot() -> None:
    health = client.get("/healthz")
    assert health.status_code == 200
    assert health.json() == {"status": "ok"}

    ready = client.get("/readyz")
    assert ready.status_code == 200
    assert ready.json() == {"status": "ready"}


def test_supported_types_is_dotted_extension_list() -> None:
    response = client.get("/api/supported-types")
    assert response.status_code == 200
    payload = response.json()
    if isinstance(payload, dict) and "extensions" in payload:
        extensions = payload["extensions"]
    else:
        extensions = payload
    assert isinstance(extensions, list)
    assert extensions
    assert all(isinstance(item, str) and item.startswith(".") for item in extensions)
    for expected in (".png", ".jpg", ".pdf", ".txt"):
        assert expected in extensions


def test_convert_png_body_is_openable_pdf() -> None:
    response = client.post(
        "/api/convert",
        files={"file": ("sample.png", _tiny_png(), "image/png")},
    )
    assert response.status_code == 200
    body = response.content
    assert b"%PDF" in body
    assert b"%%EOF" in body


def test_openapi_json_documents_convert() -> None:
    response = client.get("/openapi.json")
    assert response.status_code == 200
    spec = response.json()
    assert isinstance(spec, dict)
    paths = spec.get("paths") or {}
    assert "/api/convert" in paths
    assert spec.get("info", {}).get("title") == "Anything into PDF"


def test_requirements_txt_pins_same_core_libs_as_pyproject() -> None:
    req_names = _names_from_requirements((ROOT / "requirements.txt").read_text(encoding="utf-8"))
    data = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    pyproject_names = {
        _distribution_name(spec) for spec in data["project"]["dependencies"]
    } - {""}

    for lib in CORE_LIBS:
        assert lib in pyproject_names
        assert lib in req_names


def test_python_m_app_writes_pdf_next_to_cwd(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from app.__main__ import main

    monkeypatch.chdir(tmp_path)
    source = tmp_path / "photo.png"
    source.write_bytes(_tiny_png())

    assert main(["photo.png"]) == 0
    pdf = tmp_path / "photo.pdf"
    assert pdf.read_bytes().startswith(b"%PDF")
    assert b"%%EOF" in pdf.read_bytes()
