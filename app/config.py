from pydantic import BaseModel


class Settings(BaseModel):
    """Runtime settings for the conversion service."""

    app_name: str = "anythingintopdfbot"
    max_upload_size_bytes: int = 25 * 1024 * 1024
    allowed_extensions: set[str] = {
        ".png",
        ".jpg",
        ".jpeg",
        ".webp",
        ".bmp",
        ".tiff",
        ".tif",
        ".pdf",
        ".txt",
        ".md",
    }


settings = Settings()
