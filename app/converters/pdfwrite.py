"""Minimal PDF 1.4 writer.

img2pdf: JPEG bytes go in as /DCTDecode; other rasters as zlib /FlateDecode.
No pikepdf — objects and xref are written by hand.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class EmbeddedImage:
    width_px: int
    height_px: int
    page_width: float
    page_height: float
    data: bytes
    pdf_filter: str
    color_space: str = "DeviceRGB"


def _num(value: float) -> str:
    text = f"{value:.4f}".rstrip("0").rstrip(".")
    return text if text else "0"


def write_image_pdf(pages: list[EmbeddedImage], destination: Path) -> None:
    if not pages:
        raise ValueError("write_image_pdf needs at least one page")

    objects: dict[int, bytes] = {}
    page_ids: list[int] = []
    next_id = 3
    for page in pages:
        page_id, content_id, image_id = next_id, next_id + 1, next_id + 2
        next_id += 3
        page_ids.append(page_id)
        content = f"q {_num(page.page_width)} 0 0 {_num(page.page_height)} 0 0 cm /Im0 Do Q\n".encode("ascii")
        objects[content_id] = (
            f"<< /Length {len(content)} >>\nstream\n".encode("ascii") + content + b"endstream\n"
        )
        objects[image_id] = (
            (
                f"<< /Type /XObject /Subtype /Image /Width {page.width_px} /Height {page.height_px} "
                f"/ColorSpace /{page.color_space} /BitsPerComponent 8 "
                f"/Filter /{page.pdf_filter} /Length {len(page.data)} >>\nstream\n"
            ).encode("ascii")
            + page.data
            + b"\nendstream\n"
        )
        objects[page_id] = (
            f"<< /Type /Page /Parent 2 0 R /MediaBox [ 0 0 {_num(page.page_width)} {_num(page.page_height)} ] "
            f"/Contents {content_id} 0 R /Resources << /XObject << /Im0 {image_id} 0 R >> >> >>\n"
        ).encode("ascii")

    kids = " ".join(f"{page_id} 0 R" for page_id in page_ids)
    objects[1] = b"<< /Type /Catalog /Pages 2 0 R >>\n"
    objects[2] = f"<< /Type /Pages /Kids [{kids}] /Count {len(pages)} >>\n".encode("ascii")

    out = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets = {0: 0}
    for object_id in range(1, next_id):
        offsets[object_id] = len(out)
        out += f"{object_id} 0 obj\n".encode("ascii")
        out += objects[object_id]
        out += b"endobj\n"

    xref_at = len(out)
    out += f"xref\n0 {next_id}\n".encode("ascii")
    out += b"0000000000 65535 f \n"
    for object_id in range(1, next_id):
        out += f"{offsets[object_id]:010d} 00000 n \n".encode("ascii")
    out += (
        f"trailer\n<< /Size {next_id} /Root 1 0 R >>\nstartxref\n{xref_at}\n%%EOF\n"
    ).encode("ascii")
    destination.write_bytes(bytes(out))
