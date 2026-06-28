from pathlib import Path
from shutil import copyfile

from app.converters.base import ConversionResult


class PdfPassthroughConverter:
    """Normalize already-PDF uploads into the common conversion result contract."""

    supported_extensions = {".pdf"}

    def convert(self, source: Path, destination_dir: Path) -> ConversionResult:
        destination = destination_dir / f"{source.stem}.pdf"
        if source.resolve() != destination.resolve():
            copyfile(source, destination)
        return ConversionResult(path=destination, filename=destination.name)
