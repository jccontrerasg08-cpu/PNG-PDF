from pathlib import Path

from app.config import settings
from app.converters import UnsupportedConversionError, convert_to_pdf, get_supported_extensions
from app.converters.base import ConversionResult, extract_extension
from app.converters.merge import merge_pdfs


class ConversionRejected(Exception):
    """User-facing rejection with an HTTP-style status code."""

    def __init__(self, status_code: int, detail: str) -> None:
        self.status_code = status_code
        self.detail = detail
        super().__init__(detail)


def effective_extensions() -> set[str]:
    return get_supported_extensions() & settings.allowed_extensions


def convert_named_files(items: list[tuple[str, bytes]], destination_dir: Path) -> ConversionResult:
    """Convert one or more named in-memory files to a single PDF."""

    if not items:
        raise ConversionRejected(400, "No files were uploaded.")
    if len(items) > settings.max_upload_files:
        raise ConversionRejected(400, "Too many files.")

    total_size = 0
    results: list[ConversionResult] = []
    for index, (name, payload) in enumerate(items):
        filename = Path(name or "upload").name
        extension = extract_extension(filename)
        if extension not in effective_extensions():
            raise ConversionRejected(415, f"Unsupported file type '{extension}'.")
        total_size += len(payload)
        if total_size > settings.max_upload_size_bytes:
            raise ConversionRejected(413, "Uploaded file is too large.")
        source = destination_dir / filename
        if source.exists():
            source = destination_dir / f"{source.stem}-{index}{source.suffix}"
        source.write_bytes(payload)
        try:
            results.append(convert_to_pdf(source, destination_dir))
        except UnsupportedConversionError as exc:
            raise ConversionRejected(422, str(exc)) from exc

    if len(results) == 1:
        return results[0]
    merged = destination_dir / "converted.pdf"
    merge_pdfs([item.path for item in results], merged)
    return ConversionResult(path=merged, filename="converted.pdf")
