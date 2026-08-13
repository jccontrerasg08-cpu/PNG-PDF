import warnings
from pathlib import Path

from PIL import Image, ImageOps, UnidentifiedImageError
from pillow_heif import register_heif_opener

from app.converters.base import ConversionResult, UnsupportedConversionError, extract_extension

# pillow-heif README: register once so Image.open handles iPhone HEIC/HEIF.
register_heif_opener()

# img2pdf uses 96 when metadata is missing; Pillow PDF defaults to 72, which
# turns phone photos into poster-sized pages.
_DEFAULT_DPI = 96.0


class ImageToPdfConverter:
    """Convert raster image files into PDFs using Pillow."""

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
                with Image.open(source) as image:
                    if extract_extension(source.name) in {".heic", ".heif"} and (image.format or "").upper() not in {
                        "HEIF",
                        "HEIC",
                    }:
                        raise UnsupportedConversionError("The uploaded image could not be read.")
                    dpi = self._pdf_dpi(image)
                    frames = []
                    for frame_index in range(getattr(image, "n_frames", 1)):
                        image.seek(frame_index)
                        oriented = ImageOps.exif_transpose(image) or image
                        frames.append(self._flatten_to_rgb(oriented))

                    first_frame, *remaining_frames = frames
                    # ponytail: Pillow RGB PDF is JPEG; quality=95 until lossless embed (img2pdf) matters
                    first_frame.save(
                        destination,
                        "PDF",
                        save_all=True,
                        append_images=remaining_frames,
                        dpi=dpi,
                        quality=95,
                    )
        except (
            UnidentifiedImageError,
            OSError,
            Image.DecompressionBombError,
            Image.DecompressionBombWarning,
        ) as exc:
            raise UnsupportedConversionError("The uploaded image could not be read.") from exc

        return ConversionResult(path=destination, filename=destination.name)

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
