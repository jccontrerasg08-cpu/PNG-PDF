from pathlib import Path

from app.converters.base import extract_extension
from app.main import BASE_DIR, app


def test_extract_extension_handles_dotfile_names() -> None:
    assert extract_extension(".png") == ".png"
    assert extract_extension("photo.PNG") == ".png"
    assert extract_extension("archive.tar.gz") == ".gz"
    assert extract_extension("no-extension") == ""


def test_static_and_template_dirs_are_absolute_and_cwd_independent() -> None:
    assert BASE_DIR.is_absolute()

    static_route = next(route for route in app.routes if getattr(route, "name", None) == "static")
    static_dir = Path(static_route.app.all_directories[0])
    assert static_dir.is_absolute()
    assert static_dir.is_dir()
