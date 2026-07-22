from pathlib import Path

from PIL import Image, UnidentifiedImageError

from app.converters.base import ConversionResult, UnsupportedConversionError


class ImageToPdfConverter:
    """Convert raster image files into single-page PDFs using Pillow."""

    supported_extensions = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tiff", ".tif"}

    def convert(self, source: Path, destination_dir: Path) -> ConversionResult:
        destination = destination_dir / f"{source.stem}.pdf"
        try:
            with Image.open(source) as image:
                frames = []
                for frame_index in range(getattr(image, "n_frames", 1)):
                    image.seek(frame_index)
                    frames.append(self._flatten_to_rgb(image))

                first_frame, *remaining_frames = frames
                first_frame.save(destination, "PDF", save_all=True, append_images=remaining_frames)
        except (UnidentifiedImageError, OSError) as exc:
            raise UnsupportedConversionError("The uploaded image could not be read.") from exc

        return ConversionResult(path=destination, filename=destination.name)

    def _flatten_to_rgb(self, image: Image.Image) -> Image.Image:
        """Composite transparent pixels onto white instead of discarding alpha."""

        has_transparency = image.mode in ("RGBA", "LA") or (
            image.mode == "P" and "transparency" in image.info
        )
        if not has_transparency:
            return image.convert("RGB").copy()

        rgba = image.convert("RGBA")
        background = Image.new("RGB", rgba.size, "white")
        background.paste(rgba, mask=rgba.split()[3])
        return background
