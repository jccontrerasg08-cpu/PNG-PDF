from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from app.converters.base import ConversionResult, UnsupportedConversionError


class TextDocumentToPdfConverter:
    """Convert simple text-like documents into paginated PDF files."""

    supported_extensions = {".txt", ".md"}
    page_size = (1240, 1754)
    margin = 90
    line_spacing = 10

    def convert(self, source: Path, destination_dir: Path) -> ConversionResult:
        destination = destination_dir / f"{source.stem}.pdf"
        try:
            text = source.read_text(encoding="utf-8")
        except UnicodeDecodeError as exc:
            raise UnsupportedConversionError("Only UTF-8 text documents are supported for now.") from exc

        font = ImageFont.load_default(size=24)
        pages = self._render_pages(text or " ", font)
        first_page, *remaining_pages = pages
        first_page.save(destination, "PDF", save_all=True, append_images=remaining_pages)
        return ConversionResult(path=destination, filename=destination.name)

    def _render_pages(self, text: str, font: ImageFont.ImageFont) -> list[Image.Image]:
        pages: list[Image.Image] = []
        page = self._new_page()
        draw = ImageDraw.Draw(page)
        x = self.margin
        y = self.margin
        max_width = self.page_size[0] - (self.margin * 2)
        line_height = int(font.getbbox("Ag")[3] - font.getbbox("Ag")[1]) + self.line_spacing

        for paragraph in text.splitlines() or [""]:
            for line in self._wrap_line(paragraph, font, max_width):
                if y + line_height > self.page_size[1] - self.margin:
                    pages.append(page)
                    page = self._new_page()
                    draw = ImageDraw.Draw(page)
                    y = self.margin
                draw.text((x, y), line, fill="black", font=font)
                y += line_height
            y += line_height

        pages.append(page)
        return pages

    def _wrap_line(self, line: str, font: ImageFont.ImageFont, max_width: int) -> list[str]:
        words = line.split()
        if not words:
            return [""]

        wrapped: list[str] = []
        current = words[0]
        for word in words[1:]:
            candidate = f"{current} {word}"
            if font.getlength(candidate) <= max_width:
                current = candidate
            else:
                wrapped.append(current)
                current = word
        wrapped.append(current)
        return wrapped

    def _new_page(self) -> Image.Image:
        return Image.new("RGB", self.page_size, "white")
