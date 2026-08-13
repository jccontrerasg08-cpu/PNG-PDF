import warnings
import zlib
from pathlib import Path

from PIL import Image, ImageOps, UnidentifiedImageError
from pillow_heif import register_heif_opener

from app.converters.base import ConversionResult, UnsupportedConversionError, extract_extension
from app.converters.pdfwrite import EmbeddedImage, write_image_pdf

# pillow-heif README: register once so Image.open handles iPhone HEIC/HEIF.
register_heif_opener()

# img2pdf uses 96 when metadata is missing; Pillow PDF defaults to 72, which
# turns phone photos into poster-sized pages.
_DEFAULT_DPI = 96.0


class ImageToPdfConverter:
    """Pack raster images into a PDF the img2pdf way (JPEG as-is, else lossless Flate)."""

    supported_extensions = {
        ".png",
        ".jpg",
        ".jpeg",
        ".webp",
        ".bmp",
        ".tiff",
        ".tif",
        ".gif",
        ".heic",
        ".heif",
    }

    def convert(self, source: Path, destination_dir: Path) -> ConversionResult:
        destination = destination_dir / f"{source.stem}.pdf"
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("error", Image.DecompressionBombWarning)
                raw = source.read_bytes()
                with Image.open(source) as image:
                    if extract_extension(source.name) in {".heic", ".heif"} and (image.format or "").upper() not in {
                        "HEIF",
                        "HEIC",
                    }:
                        raise UnsupportedConversionError("The uploaded image could not be read.")
                    pages = self._pages(image, raw)
        except (
            UnidentifiedImageError,
            OSError,
            Image.DecompressionBombError,
            Image.DecompressionBombWarning,
        ) as exc:
            raise UnsupportedConversionError("The uploaded image could not be read.") from exc

        write_image_pdf(pages, destination)
        return ConversionResult(path=destination, filename=destination.name)

    def _pages(self, image: Image.Image, raw: bytes) -> list[EmbeddedImage]:
        if self._can_embed_jpeg(image):
            width, height = image.size
            page_w, page_h = self._page_points(width, height, image)
            color_space = "DeviceGray" if image.mode == "L" else "DeviceRGB"
            return [
                EmbeddedImage(
                    width_px=width,
                    height_px=height,
                    page_width=page_w,
                    page_height=page_h,
                    data=raw,
                    pdf_filter="DCTDecode",
                    color_space=color_space,
                )
            ]

        frames: list[EmbeddedImage] = []
        for frame_index in range(getattr(image, "n_frames", 1)):
            image.seek(frame_index)
            oriented = ImageOps.exif_transpose(image) or image
            rgb = self._flatten_to_rgb(oriented)
            width, height = rgb.size
            page_w, page_h = self._page_points(width, height, oriented)
            frames.append(
                EmbeddedImage(
                    width_px=width,
                    height_px=height,
                    page_width=page_w,
                    page_height=page_h,
                    data=zlib.compress(rgb.tobytes(), 6),
                    pdf_filter="FlateDecode",
                    color_space="DeviceRGB",
                )
            )
        return frames

    def _can_embed_jpeg(self, image: Image.Image) -> bool:
        if (image.format or "").upper() != "JPEG":
            return False
        if getattr(image, "n_frames", 1) != 1:
            return False
        if image.mode not in {"RGB", "L"}:
            return False
        orientation = image.getexif().get(274, 1) or 1
        return orientation == 1

    def _page_points(self, width: int, height: int, image: Image.Image) -> tuple[float, float]:
        dpi_x, dpi_y = self._pdf_dpi(image)
        return (width * 72.0 / dpi_x, height * 72.0 / dpi_y)

    def _pdf_dpi(self, image: Image.Image) -> tuple[float, float]:
        dpi = image.info.get("dpi")
        if not dpi or dpi[0] < 2 or dpi[1] < 2:
            return (_DEFAULT_DPI, _DEFAULT_DPI)
        return (float(dpi[0]), float(dpi[1]))

    def _flatten_to_rgb(self, image: Image.Image) -> Image.Image:
        """Composite transparent pixels onto white instead of discarding alpha."""

        has_transparency = image.mode in ("RGBA", "LA", "PA", "RGBa") or (
            image.mode == "P" and "transparency" in image.info
        )
        if not has_transparency:
            return image.convert("RGB").copy()

        rgba = image.convert("RGBA")
        background = Image.new("RGB", rgba.size, "white")
        background.paste(rgba, mask=rgba.split()[3])
        return background
