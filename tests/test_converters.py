from pathlib import Path

import pytest
from PIL import Image, ImageFont

from app.converters.base import UnsupportedConversionError
from app.converters.documents import TextDocumentToPdfConverter
from app.converters.images import ImageToPdfConverter


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
