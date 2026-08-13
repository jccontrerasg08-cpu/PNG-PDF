"""Convert files to PDF from the command line: python -m app photo.png notes.txt"""

from __future__ import annotations

import sys
from pathlib import Path
from shutil import copy2, rmtree
from tempfile import mkdtemp

from app.converters import UnsupportedConversionError, convert_to_pdf
from app.converters.merge import merge_pdfs


def main(argv: list[str] | None = None) -> int:
    paths = [Path(item) for item in (sys.argv[1:] if argv is None else argv)]
    if not paths:
        print("Usage: python -m app FILE [FILE ...]", file=sys.stderr)
        return 2

    missing = [path for path in paths if not path.is_file()]
    if missing:
        print(f"Not a file: {missing[0]}", file=sys.stderr)
        return 2

    temp_dir = Path(mkdtemp(prefix="anythingintopdfbot-"))
    try:
        results = [convert_to_pdf(path, temp_dir) for path in paths]
        if len(results) == 1:
            output = Path.cwd() / results[0].filename
            copy2(results[0].path, output)
        else:
            output = Path.cwd() / "converted.pdf"
            merge_pdfs([item.path for item in results], output)
        print(output)
        return 0
    except UnsupportedConversionError as exc:
        print(exc, file=sys.stderr)
        return 1
    finally:
        rmtree(temp_dir, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
