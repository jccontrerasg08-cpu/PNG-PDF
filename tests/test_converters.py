import re
from pathlib import Path

import pytest
from PIL import Image, ImageFont

from app.converters.base import UnsupportedConversionError
from app.converters.documents import TextDocumentToPdfConverter
from app.converters.images import ImageToPdfConverter
from app.converters.pdf import PdfPassthroughConverter


def _pdf_mediabox(pdf_bytes: bytes) -> tuple[float, float]:
    match = re.search(rb"/MediaBox \[ 0 0 ([0-9.]+) ([0-9.]+) \]", pdf_bytes)
    assert match, pdf_bytes[:400]
    return float(match.group(1)), float(match.group(2))


def test_transparent_png_composites_onto_white_not_black(tmp_path: Path) -> None:
    source = tmp_path / "transparent.png"
    # Fully transparent pixel with black RGB underneath - the common case for
    # editor-exported PNGs with a "transparent" background.
    Image.new("RGBA", (4, 4), (0, 0, 0, 0)).save(source)

    converter = ImageToPdfConverter()
    frame = converter._flatten_to_rgb(Image.open(source))

    assert frame.mode == "RGB"
    assert frame.getpixel((0, 0)) == (255, 255, 255)


def test_opaque_image_is_unaffected_by_flattening(tmp_path: Path) -> None:
    source = tmp_path / "opaque.png"
    Image.new("RGB", (4, 4), (10, 20, 30)).save(source)

    converter = ImageToPdfConverter()
    frame = converter._flatten_to_rgb(Image.open(source))

    assert frame.getpixel((0, 0)) == (10, 20, 30)


def test_truncated_image_raises_unsupported_conversion_error(tmp_path: Path) -> None:
    good_bytes = tmp_path / "good.png"
    Image.new("RGB", (64, 64), "red").save(good_bytes, format="PNG")
    truncated = tmp_path / "broken.png"
    truncated.write_bytes(good_bytes.read_bytes()[: good_bytes.stat().st_size // 2])

    converter = ImageToPdfConverter()
    with pytest.raises(UnsupportedConversionError):
        converter.convert(truncated, tmp_path)


def test_unbroken_long_word_is_hard_wrapped_within_page_width() -> None:
    converter = TextDocumentToPdfConverter()
    font = ImageFont.load_default(size=24)
    max_width = converter.page_size[0] - (converter.margin * 2)
    long_token = "x" * 400

    lines = converter._wrap_line(long_token, font, max_width)

    assert len(lines) > 1
    for line in lines:
        assert font.getlength(line) <= max_width
    assert "".join(lines) == long_token


def test_exif_orientation_6_rotates_page_to_portrait(tmp_path: Path) -> None:
    source = tmp_path / "sideways.jpg"
    image = Image.new("RGB", (80, 40), "red")
    exif = image.getexif()
    exif[274] = 6  # rotate 90° CW
    image.save(source, format="JPEG", exif=exif)

    result = ImageToPdfConverter().convert(source, tmp_path)
    width, height = _pdf_mediabox(result.path.read_bytes())

    assert height > width


def test_image_pdf_uses_96_dpi_when_metadata_missing(tmp_path: Path) -> None:
    source = tmp_path / "square.png"
    Image.new("RGB", (96, 96), "blue").save(source)

    result = ImageToPdfConverter().convert(source, tmp_path)
    width, height = _pdf_mediabox(result.path.read_bytes())

    assert width == pytest.approx(72.0)
    assert height == pytest.approx(72.0)


def test_decompression_bomb_is_rejected(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(Image, "MAX_IMAGE_PIXELS", 64)
    source = tmp_path / "bomb.png"
    Image.new("RGB", (32, 32), "red").save(source)

    with pytest.raises(UnsupportedConversionError):
        ImageToPdfConverter().convert(source, tmp_path)


def test_near_limit_image_is_rejected_as_decompression_bomb(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(Image, "MAX_IMAGE_PIXELS", 1000)
    source = tmp_path / "large.png"
    Image.new("RGB", (32, 32), "red").save(source)

    with pytest.raises(UnsupportedConversionError):
        ImageToPdfConverter().convert(source, tmp_path)


def test_valid_pdf_is_passthrough(tmp_path: Path) -> None:
    source = tmp_path / "ok.pdf"
    payload = b"%PDF-1.4\n1 0 obj<<>>endobj\ntrailer<<>>\n%%EOF\n"
    source.write_bytes(payload)

    result = PdfPassthroughConverter().convert(source, tmp_path)

    assert result.path.read_bytes() == payload


def test_non_pdf_bytes_named_pdf_are_rejected(tmp_path: Path) -> None:
    source = tmp_path / "fake.pdf"
    source.write_bytes(b"\x89PNG\r\n\x1a\nnot-a-pdf")

    with pytest.raises(UnsupportedConversionError, match="not a valid PDF"):
        PdfPassthroughConverter().convert(source, tmp_path)


def test_latin1_text_is_rejected(tmp_path: Path) -> None:
    source = tmp_path / "latin1.txt"
    source.write_bytes("café".encode("latin-1"))

    with pytest.raises(UnsupportedConversionError, match="UTF-8"):
        TextDocumentToPdfConverter().convert(source, tmp_path)


def test_utf8_bom_text_converts(tmp_path: Path) -> None:
    source = tmp_path / "bom.txt"
    source.write_bytes("hello".encode("utf-8-sig"))

    result = TextDocumentToPdfConverter().convert(source, tmp_path)

    assert result.path.read_bytes().startswith(b"%PDF")


def test_text_pdf_page_is_a4_sized(tmp_path: Path) -> None:
    source = tmp_path / "note.txt"
    source.write_text("hello\n", encoding="utf-8")

    result = TextDocumentToPdfConverter().convert(source, tmp_path)
    width, height = _pdf_mediabox(result.path.read_bytes())

    assert width == pytest.approx(1240 * 72 / 150)
    assert height == pytest.approx(1754 * 72 / 150)


def test_text_over_max_pages_is_rejected(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(TextDocumentToPdfConverter, "max_pages", 1)
    source = tmp_path / "long.txt"
    source.write_text("\n".join(["line"] * 80), encoding="utf-8")

    with pytest.raises(UnsupportedConversionError, match="too many pages"):
        TextDocumentToPdfConverter().convert(source, tmp_path)
