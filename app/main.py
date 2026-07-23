from pathlib import Path
from shutil import rmtree
from tempfile import mkdtemp

from fastapi import FastAPI, File, HTTPException, Request, UploadFile, status
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from starlette.background import BackgroundTask
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.config import settings
from app.converters import UnsupportedConversionError, convert_to_pdf, get_supported_extensions
from app.converters.base import extract_extension

BASE_DIR = Path(__file__).resolve().parent

app = FastAPI(title=settings.app_name, version="0.1.0")
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
templates = Jinja2Templates(directory=BASE_DIR / "templates")


def _effective_extensions() -> set[str]:
    """Extensions that are both technically convertible and allowed by settings."""

    return get_supported_extensions() & settings.allowed_extensions


@app.get("/healthz", tags=["health"])
def healthz() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/readyz", tags=["health"])
def readyz() -> dict[str, str]:
    return {"status": "ready"}


@app.get("/", response_class=HTMLResponse, tags=["web"])
def index(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(
        request,
        "index.html",
        {"supported_extensions": sorted(_effective_extensions())},
    )


@app.get("/api/supported-types", tags=["conversion"])
def supported_types() -> dict[str, list[str]]:
    return {"extensions": sorted(_effective_extensions())}


@app.post("/api/convert", tags=["conversion"])
async def convert(file: UploadFile = File(...)) -> FileResponse:
    filename = Path(file.filename or "upload").name
    extension = extract_extension(filename)
    if extension not in _effective_extensions():
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Unsupported file type '{extension}'.",
        )

    chunk_size = 1024 * 1024
    chunks: list[bytes] = []
    total_size = 0
    while chunk := await file.read(chunk_size):
        total_size += len(chunk)
        if total_size > settings.max_upload_size_bytes:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail="Uploaded file is too large.",
            )
        chunks.append(chunk)
    contents = b"".join(chunks)

    temp_dir = Path(mkdtemp(prefix="anythingintopdfbot-"))
    try:
        source = temp_dir / filename
        source.write_bytes(contents)
        result = convert_to_pdf(source, temp_dir)
        return FileResponse(
            result.path,
            media_type=result.media_type,
            filename=result.filename,
            background=BackgroundTask(rmtree, temp_dir, ignore_errors=True),
        )
    except UnsupportedConversionError as exc:
        rmtree(temp_dir, ignore_errors=True)
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    except Exception:
        rmtree(temp_dir, ignore_errors=True)
        raise


@app.exception_handler(HTTPException)
def http_exception_handler(_: Request, exc: HTTPException) -> JSONResponse:
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})
