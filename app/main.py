import os
from pathlib import Path
from shutil import rmtree
from tempfile import mkdtemp

from fastapi import FastAPI, File, HTTPException, Request, UploadFile, status
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, Response
from starlette.background import BackgroundTask
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.config import settings, telegram_bot_username
from app.converters.base import extract_extension
from app.jobs import ConversionRejected, convert_named_files, effective_extensions
from app.telegram import TelegramApi, handle_update

BASE_DIR = Path(__file__).resolve().parent

app = FastAPI(
    title=settings.display_name,
    description="Convert photos, Office, SVG, and text to PDF. Web, API, CLI, and Telegram. Files are not stored.",
    version=settings.version,
)
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
templates = Jinja2Templates(directory=BASE_DIR / "templates")


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
        {
            "supported_extensions": sorted(effective_extensions()),
            "display_name": settings.display_name,
            "telegram_bot_username": telegram_bot_username(),
        },
    )


@app.get("/api/supported-types", tags=["conversion"])
def supported_types() -> dict[str, list[str]]:
    return {"extensions": sorted(effective_extensions())}


@app.post("/api/convert", tags=["conversion"])
async def convert(file: list[UploadFile] = File(...)) -> FileResponse:
    if len(file) > settings.max_upload_files:
        raise HTTPException(status_code=400, detail="Too many files.")

    for upload in file:
        filename = Path(upload.filename or "upload").name
        extension = extract_extension(filename)
        if extension not in effective_extensions():
            raise HTTPException(
                status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                detail=f"Unsupported file type '{extension}'.",
            )

    temp_dir = Path(mkdtemp(prefix="anythingintopdfbot-"))
    items: list[tuple[str, bytes]] = []
    total_size = 0
    try:
        for upload in file:
            filename = Path(upload.filename or "upload").name
            chunks: list[bytes] = []
            while chunk := await upload.read(1024 * 1024):
                total_size += len(chunk)
                if total_size > settings.max_upload_size_bytes:
                    raise HTTPException(status_code=413, detail="Uploaded file is too large.")
                chunks.append(chunk)
            items.append((filename, b"".join(chunks)))

        result = convert_named_files(items, temp_dir)
        return FileResponse(
            result.path,
            media_type=result.media_type,
            filename=result.filename,
            background=BackgroundTask(rmtree, temp_dir, ignore_errors=True),
        )
    except HTTPException:
        rmtree(temp_dir, ignore_errors=True)
        raise
    except ConversionRejected as exc:
        rmtree(temp_dir, ignore_errors=True)
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
    except Exception:
        rmtree(temp_dir, ignore_errors=True)
        raise


@app.post("/telegram/webhook", tags=["telegram"])
async def telegram_webhook(request: Request) -> dict[str, bool]:
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    if not token:
        raise HTTPException(status_code=404, detail="Not found.")
    secret = os.environ.get("TELEGRAM_WEBHOOK_SECRET", "").strip()
    if secret and request.headers.get("x-telegram-bot-api-secret-token") != secret:
        raise HTTPException(status_code=403, detail="Forbidden.")
    update = await request.json()
    try:
        handle_update(update, TelegramApi(token))
    except Exception:
        pass
    return {"ok": True}


@app.exception_handler(HTTPException)
def http_exception_handler(request: Request, exc: HTTPException) -> HTMLResponse | JSONResponse:
    if _wants_html(request):
        return templates.TemplateResponse(
            request,
            "error.html",
            {"detail": exc.detail, "status_code": exc.status_code, "display_name": settings.display_name},
            status_code=exc.status_code,
        )
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})
