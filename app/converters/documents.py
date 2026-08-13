from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from app.converters.base import ConversionResult, UnsupportedConversionError


class TextDocumentToPdfConverter:
    """Convert simple text-like documents into paginated PDF files."""

    supported_extensions = {".txt", ".md"}
    page_size = (1240, 1754)  # A4 pixels at 150 DPI
    margin = 90
    line_spacing = 10
    max_pages = 20
    pdf_dpi = 150.0

    def convert(self, source: Path, destination_dir: Path) -> ConversionResult:
        destination = destination_dir / f"{source.stem}.pdf"
        try:
            text = source.read_text(encoding="utf-8-sig")
        except UnicodeDecodeError as exc:
            raise UnsupportedConversionError("Only UTF-8 text documents are supported for now.") from exc

        font = ImageFont.load_default(size=24)
        pages = self._render_pages(text or " ", font)
        first_page, *remaining_pages = pages
        first_page.save(
            destination,
            "PDF",
            save_all=True,
            append_images=remaining_pages,
            resolution=self.pdf_dpi,
        )
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
                    if len(pages) >= self.max_pages:
                        raise UnsupportedConversionError(
                            "The uploaded text document has too many pages."
                        )
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
        current = ""
        for word in words:
            for chunk in self._split_word(word, font, max_width):
                candidate = f"{current} {chunk}" if current else chunk
                if current and font.getlength(candidate) > max_width:
                    wrapped.append(current)
                    current = chunk
                else:
                    current = candidate
        wrapped.append(current)
        return wrapped

    def _split_word(self, word: str, font: ImageFont.ImageFont, max_width: int) -> list[str]:
        """Hard-break a single word that is wider than max_width on its own."""

        if font.getlength(word) <= max_width:
            return [word]

        pieces: list[str] = []
        current = ""
        for char in word:
            candidate = current + char
            if current and font.getlength(candidate) > max_width:
                pieces.append(current)
                current = char
            else:
                current = candidate
        if current:
            pieces.append(current)
        return pieces

    def _new_page(self) -> Image.Image:
        return Image.new("RGB", self.page_size, "white")
