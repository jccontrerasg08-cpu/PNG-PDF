"""Old .doc / LibreOffice fidelity — skipped when soffice is not installed."""

from __future__ import annotations

import shutil
from io import BytesIO
from pathlib import Path

import pytest
from docx import Document
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)
HAS_SOFFICE = bool(shutil.which("soffice") or shutil.which("libreoffice"))


def _docx_bytes() -> bytes:
    buffer = BytesIO()
    document = Document()
    document.add_paragraph("Legacy Word round-trip")
    document.save(buffer)
    return buffer.getvalue()


@pytest.mark.skipif(not HAS_SOFFICE, reason="LibreOffice (soffice) is not installed")
def test_old_doc_converts_to_pdf(tmp_path: Path) -> None:
    from app.converters.libreoffice import convert_with_soffice

    source_docx = tmp_path / "letter.docx"
    source_docx.write_bytes(_docx_bytes())
    convert_with_soffice(source_docx, tmp_path, target="doc")
    legacy = tmp_path / "letter.doc"
    assert legacy.exists()

    response = client.post(
        "/api/convert",
        files={"file": ("letter.doc", legacy.read_bytes(), "application/msword")},
    )
    assert response.status_code == 200
    assert response.content.startswith(b"%PDF")


@pytest.mark.skipif(not HAS_SOFFICE, reason="LibreOffice (soffice) is not installed")
def test_docx_via_libreoffice_is_a_real_pdf() -> None:
    response = client.post(
        "/api/convert",
        files={
            "file": (
                "letter.docx",
                _docx_bytes(),
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )
        },
    )
    assert response.status_code == 200
    body = response.content
    assert body.startswith(b"%PDF")
    # Writer PDFs contain a font/text stream; the text fallback is a raster image PDF.
    assert b"/Font" in body or b"/Type /Font" in body


def test_garbage_doc_returns_422() -> None:
    response = client.post(
        "/api/convert",
        files={"file": ("broken.doc", b"not ole storage", "application/msword")},
    )
    assert response.status_code == 422


@pytest.mark.skipif(not HAS_SOFFICE, reason="LibreOffice (soffice) is not installed")
def test_rtf_converts_to_pdf() -> None:
    rtf = br"{\rtf1\ansi\deff0{\fonttbl{\f0 Times New Roman;}}\f0\fs24 Hello RTF\par}"
    response = client.post(
        "/api/convert",
        files={"file": ("note.rtf", rtf, "application/rtf")},
    )
    assert response.status_code == 200
    assert response.content.startswith(b"%PDF")
