from pathlib import Path

from app.converters.base import ConversionResult, Converter, UnsupportedConversionError, extract_extension
from app.converters.documents import TextDocumentToPdfConverter
from app.converters.images import ImageToPdfConverter
from app.converters.office import OfficeToPdfConverter
from app.converters.pdf import PdfPassthroughConverter

_CONVERTERS: tuple[Converter, ...] = (
    PdfPassthroughConverter(),
    ImageToPdfConverter(),
    TextDocumentToPdfConverter(),
    OfficeToPdfConverter(),
)


def get_supported_extensions() -> set[str]:
    """Return all file extensions currently supported by registered converters."""

    return {extension for converter in _CONVERTERS for extension in converter.supported_extensions}


def convert_to_pdf(source: Path, destination_dir: Path) -> ConversionResult:
    """Convert source to PDF using the converter registered for its extension."""

    extension = extract_extension(source.name)
    for converter in _CONVERTERS:
        if extension in converter.supported_extensions:
            return converter.convert(source, destination_dir)
    raise UnsupportedConversionError(f"Files with extension '{extension}' are not supported yet.")
