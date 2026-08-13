"""Convert files to PDF from the command line: python -m app photo.png notes.txt"""

from __future__ import annotations

import sys
from pathlib import Path
from shutil import copy2, rmtree
from tempfile import mkdtemp

from app.jobs import ConversionRejected, convert_named_files


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
        items = [(path.name, path.read_bytes()) for path in paths]
        result = convert_named_files(items, temp_dir)
        output = Path.cwd() / result.filename
        copy2(result.path, output)
        print(output)
        return 0
    except ConversionRejected as exc:
        print(exc.detail, file=sys.stderr)
        return 1
    finally:
        rmtree(temp_dir, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
