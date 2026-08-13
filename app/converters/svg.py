from pathlib import Path

from app.converters.base import ConversionResult, UnsupportedConversionError


class SvgToPdfConverter:
    """SVG → PDF via CairoSVG; LibreOffice Draw if CairoSVG is not installed."""

    supported_extensions = {".svg", ".svgz"}

    def convert(self, source: Path, destination_dir: Path) -> ConversionResult:
        destination = destination_dir / f"{source.stem}.pdf"
        try:
            import cairosvg
        except ImportError:
            self._convert_with_soffice(source, destination_dir)
        else:
            try:
                cairosvg.svg2pdf(url=str(source), write_to=str(destination))
            except Exception as exc:
                raise UnsupportedConversionError("The uploaded SVG could not be read.") from exc

        if not destination.exists() or not destination.read_bytes().startswith(b"%PDF"):
            raise UnsupportedConversionError("The uploaded SVG could not be read.")
        return ConversionResult(path=destination, filename=destination.name)

    def _convert_with_soffice(self, source: Path, destination_dir: Path) -> None:
        from app.converters.libreoffice import convert_with_soffice, soffice_available

        if not soffice_available():
            raise UnsupportedConversionError("The uploaded SVG could not be read.")
        convert_with_soffice(source, destination_dir, target="pdf")
