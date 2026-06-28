from dataclasses import dataclass
from pathlib import Path
from typing import Protocol


@dataclass(frozen=True)
class ConversionResult:
    """A converted PDF ready to be returned to a client."""

    path: Path
    filename: str
    media_type: str = "application/pdf"


class UnsupportedConversionError(ValueError):
    """Raised when a file type cannot be converted by the service."""


class Converter(Protocol):
    """Document converter interface."""

    supported_extensions: set[str]

    def convert(self, source: Path, destination_dir: Path) -> ConversionResult:
        """Convert source into a PDF stored in destination_dir."""
