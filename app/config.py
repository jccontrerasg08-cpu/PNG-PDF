from pydantic import BaseModel


class Settings(BaseModel):
    """Runtime settings for the conversion service."""

    app_name: str = "anythingintopdfbot"
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


settings = Settings()
