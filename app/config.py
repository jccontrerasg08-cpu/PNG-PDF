import os
from pathlib import Path

from pydantic import BaseModel


def _load_dotenv() -> None:
    """Load `.env` without overriding real environment variables. Token stays out of git."""

    for candidate in (Path.cwd() / ".env", Path(__file__).resolve().parent.parent / ".env"):
        if not candidate.is_file():
            continue
        for raw in candidate.read_text(encoding="utf-8").splitlines():
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            os.environ.setdefault(key.strip(), value.strip().strip("'").strip('"'))
        break


_load_dotenv()


class Settings(BaseModel):
    """Runtime settings for the conversion service."""

    app_name: str = "anythingintopdfbot"
    display_name: str = "Anything into PDF"
    version: str = "0.2.0"
    max_upload_size_bytes: int = 25 * 1024 * 1024
    max_upload_files: int = 10
    allowed_extensions: set[str] = {
        ".png",
        ".jpg",
        ".jpeg",
        ".webp",
        ".bmp",
        ".tiff",
        ".tif",
        ".gif",
        ".heic",
        ".heif",
        ".pdf",
        ".txt",
        ".md",
        ".docx",
        ".xlsx",
        ".pptx",
        ".doc",
        ".xls",
        ".ppt",
        ".odt",
        ".ods",
        ".odp",
        ".rtf",
        ".svg",
        ".svgz",
    }


def telegram_bot_username() -> str:
    return os.environ.get("TELEGRAM_BOT_USERNAME", "").lstrip("@")


settings = Settings()
