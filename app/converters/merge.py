from pathlib import Path

from pypdf import PdfWriter


def merge_pdfs(paths: list[Path], destination: Path) -> Path:
    """Join PDFs in order. Copied from the pypdf merging docs (PdfWriter.append)."""

    merger = PdfWriter()
    for pdf in paths:
        merger.append(str(pdf))
    merger.write(str(destination))
    merger.close()
    return destination
