from pathlib import Path
from shutil import copyfile

from app.converters.base import ConversionResult, UnsupportedConversionError


class PdfPassthroughConverter:
    """Pass through already-PDF uploads after a magic-byte check."""

    supported_extensions = {".pdf"}

    def convert(self, source: Path, destination_dir: Path) -> ConversionResult:
        header = source.read_bytes()[:1024]
        if b"%PDF-" not in header:
            raise UnsupportedConversionError("The uploaded file is not a valid PDF.")

        destination = destination_dir / f"{source.stem}.pdf"
        if source.resolve() != destination.resolve():
            copyfile(source, destination)
        return ConversionResult(path=destination, filename=destination.name)
