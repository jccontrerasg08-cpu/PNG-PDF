from __future__ import annotations

import os
import shutil
import subprocess
import uuid
from pathlib import Path

from app.converters.base import ConversionResult, UnsupportedConversionError

# Gotenberg / Ask LibreOffice: isolate the user profile so two Gunicorn workers
# can convert at once without sharing a GUI soffice lock.


def _soffice_bin() -> str | None:
    return shutil.which("soffice") or shutil.which("libreoffice")


def soffice_available() -> bool:
    return _soffice_bin() is not None


# What LibreOffice needs to start. It opens untrusted documents, so it gets
# none of the service's own secrets (TELEGRAM_BOT_TOKEN and the like).
_PASSTHROUGH_ENV = ("PATH", "LANG", "LC_ALL", "LC_CTYPE", "TZ", "TMPDIR", "TEMP", "TMP", "SYSTEMROOT")


def _conversion_env(home: Path) -> dict[str, str]:
    env = {name: os.environ[name] for name in _PASSTHROUGH_ENV if name in os.environ}
    env["HOME"] = str(home)
    return env


def convert_with_soffice(source: Path, destination_dir: Path, target: str = "pdf") -> Path:
    """Run headless LibreOffice. `target` is pdf, doc, etc."""

    binary = _soffice_bin()
    if binary is None:
        raise UnsupportedConversionError("LibreOffice is not installed.")

    profile = destination_dir / f"lo-profile-{uuid.uuid4().hex}"
    profile.mkdir(parents=True, exist_ok=True)
    env = _conversion_env(destination_dir)
    command = [
        binary,
        "--headless",
        "--invisible",
        "--nologo",
        "--nolockcheck",
        "--nodefault",
        "--nofirststartwizard",
        "--norestore",
        f"-env:UserInstallation={profile.resolve().as_uri()}",
        "--convert-to",
        target,
        "--outdir",
        str(destination_dir),
        str(source),
    ]
    try:
        completed = subprocess.run(
            command,
            check=False,
            capture_output=True,
            timeout=90,
            env=env,
            stdin=subprocess.DEVNULL,
        )
    except subprocess.TimeoutExpired as exc:
        raise UnsupportedConversionError("LibreOffice timed out converting this file.") from exc

    output = destination_dir / f"{source.stem}.{target}"
    if completed.returncode != 0 or not output.exists():
        raise UnsupportedConversionError("LibreOffice could not convert this file.")
    return output


class LibreOfficeToPdfConverter:
    """High-fidelity PDF via soffice for Word/Excel/PowerPoint/OpenDocument/RTF."""

    supported_extensions = {
        ".doc",
        ".docx",
        ".xls",
        ".xlsx",
        ".ppt",
        ".pptx",
        ".odt",
        ".ods",
        ".odp",
        ".rtf",
    }

    def convert(self, source: Path, destination_dir: Path) -> ConversionResult:
        pdf_path = convert_with_soffice(source, destination_dir, target="pdf")
        return ConversionResult(path=pdf_path, filename=pdf_path.name)
