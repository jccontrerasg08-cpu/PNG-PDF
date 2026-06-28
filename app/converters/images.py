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
                    frames.append(image.convert("RGB").copy())

                first_frame, *remaining_frames = frames
                first_frame.save(destination, "PDF", save_all=True, append_images=remaining_frames)
        except UnidentifiedImageError as exc:
            raise UnsupportedConversionError("The uploaded image could not be read.") from exc

        return ConversionResult(path=destination, filename=destination.name)
