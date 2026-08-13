from pathlib import Path
from shutil import rmtree
from tempfile import mkdtemp

from fastapi import FastAPI, File, HTTPException, Request, UploadFile, status
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, Response
from starlette.background import BackgroundTask
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.config import settings
from app.converters import UnsupportedConversionError, convert_to_pdf, get_supported_extensions
from app.converters.base import ConversionResult, extract_extension
from app.converters.merge import merge_pdfs

BASE_DIR = Path(__file__).resolve().parent

app = FastAPI(title=settings.app_name, version="0.1.0")
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
templates = Jinja2Templates(directory=BASE_DIR / "templates")


def _effective_extensions() -> set[str]:
    """Extensions that are both technically convertible and allowed by settings."""

    return get_supported_extensions() & settings.allowed_extensions


def _wants_html(request: Request) -> bool:
    return "text/html" in request.headers.get("accept", "")


@app.get("/healthz", tags=["health"])
def healthz() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/readyz", tags=["health"])
def readyz() -> dict[str, str]:
    return {"status": "ready"}


@app.get("/favicon.ico", include_in_schema=False)
def favicon() -> Response:
    return Response(status_code=204)


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
async def convert(file: list[UploadFile] = File(...)) -> FileResponse:
    if len(file) > settings.max_upload_files:
        raise HTTPException(status_code=400, detail="Too many files.")

    for upload in file:
        filename = Path(upload.filename or "upload").name
        extension = extract_extension(filename)
        if extension not in _effective_extensions():
            raise HTTPException(
                status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                detail=f"Unsupported file type '{extension}'.",
            )

    temp_dir = Path(mkdtemp(prefix="anythingintopdfbot-"))
    results: list[ConversionResult] = []
    total_size = 0
    try:
        for index, upload in enumerate(file):
            filename = Path(upload.filename or "upload").name
            chunks: list[bytes] = []
            while chunk := await upload.read(1024 * 1024):
                total_size += len(chunk)
                if total_size > settings.max_upload_size_bytes:
                    raise HTTPException(status_code=413, detail="Uploaded file is too large.")
                chunks.append(chunk)
            source = temp_dir / filename
            if source.exists():
                source = temp_dir / f"{source.stem}-{index}{source.suffix}"
            source.write_bytes(b"".join(chunks))
            results.append(convert_to_pdf(source, temp_dir))

        if len(results) == 1:
            result = results[0]
        else:
            merged = temp_dir / "converted.pdf"
            merge_pdfs([item.path for item in results], merged)
            result = ConversionResult(path=merged, filename="converted.pdf")

        return FileResponse(
            result.path,
            media_type=result.media_type,
            filename=result.filename,
            background=BackgroundTask(rmtree, temp_dir, ignore_errors=True),
        )
    except HTTPException:
        rmtree(temp_dir, ignore_errors=True)
        raise
    except UnsupportedConversionError as exc:
        rmtree(temp_dir, ignore_errors=True)
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception:
        rmtree(temp_dir, ignore_errors=True)
        raise


@app.exception_handler(HTTPException)
def http_exception_handler(request: Request, exc: HTTPException) -> HTMLResponse | JSONResponse:
    if _wants_html(request):
        return templates.TemplateResponse(
            request,
            "error.html",
            {"detail": exc.detail, "status_code": exc.status_code},
            status_code=exc.status_code,
        )
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})
