"""Optional Telegram adapter: send a file, get a PDF back.

Doc2Pdf-bot / iLovePDF pattern, without Pyrogram. Bot API over urllib.
Set TELEGRAM_BOT_TOKEN. Local: python -m app.telegram. Deployed: POST /telegram/webhook.
"""

from __future__ import annotations

import json
import os
import sys
import urllib.request
from pathlib import Path
from shutil import rmtree
from tempfile import mkdtemp
from typing import Callable

from app.jobs import ConversionRejected, convert_named_files, effective_extensions

OpenUrl = Callable[..., object]
API_ROOT = "https://api.telegram.org"


class TelegramApi:
    def __init__(self, token: str, opener: OpenUrl | None = None) -> None:
        self.token = token
        self._opener = opener or urllib.request.urlopen

    def call(self, method: str, payload: dict | None = None) -> dict:
        request = urllib.request.Request(
            f"{API_ROOT}/bot{self.token}/{method}",
            data=json.dumps(payload or {}).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with self._opener(request, timeout=60) as response:
            body = json.loads(response.read().decode("utf-8"))
        if not body.get("ok"):
            raise RuntimeError(body.get("description") or f"Telegram {method} failed")
        return body["result"]

    def download(self, file_path: str) -> bytes:
        url = f"{API_ROOT}/file/bot{self.token}/{file_path}"
        with self._opener(url, timeout=60) as response:
            return response.read()

    def send_message(self, chat_id: int, text: str) -> None:
        self.call("sendMessage", {"chat_id": chat_id, "text": text})

    def send_document(self, chat_id: int, filename: str, data: bytes) -> None:
        boundary = "----anythingintopdfbot"
        safe_name = Path(filename).name.encode("ascii", "replace").decode("ascii")
        chunks = [
            (
                f"--{boundary}\r\nContent-Disposition: form-data; name=\"chat_id\"\r\n\r\n"
                f"{chat_id}\r\n"
            ).encode("ascii"),
            (
                f"--{boundary}\r\nContent-Disposition: form-data; name=\"document\"; "
                f"filename=\"{safe_name}\"\r\nContent-Type: application/pdf\r\n\r\n"
            ).encode("ascii"),
            data,
            f"\r\n--{boundary}--\r\n".encode("ascii"),
        ]
        request = urllib.request.Request(
            f"{API_ROOT}/bot{self.token}/sendDocument",
            data=b"".join(chunks),
            headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
            method="POST",
        )
        with self._opener(request, timeout=60) as response:
            body = json.loads(response.read().decode("utf-8"))
        if not body.get("ok"):
            raise RuntimeError(body.get("description") or "Telegram sendDocument failed")


def _help_text() -> str:
    types = ", ".join(sorted(effective_extensions()))
    return (
        "Send a photo or file and I will reply with a PDF. Files are not stored.\n"
        f"Supported: {types}"
    )


def _incoming_file(message: dict) -> tuple[str, str] | None:
    document = message.get("document")
    if document and document.get("file_id"):
        return document["file_id"], document.get("file_name") or "upload.bin"
    photos = message.get("photo") or []
    if photos:
        return photos[-1]["file_id"], "photo.jpg"
    return None


def handle_update(update: dict, api: TelegramApi) -> None:
    message = update.get("message") or {}
    chat = message.get("chat") or {}
    chat_id = chat.get("id")
    if chat_id is None:
        return

    text = (message.get("text") or "").strip()
    if text.startswith("/start") or text.startswith("/help"):
        api.send_message(chat_id, _help_text())
        return

    incoming = _incoming_file(message)
    if incoming is None:
        api.send_message(chat_id, "Send a photo or file to convert to PDF.")
        return

    file_id, filename = incoming
    info = api.call("getFile", {"file_id": file_id})
    file_path = info.get("file_path")
    if not file_path:
        api.send_message(chat_id, "Telegram did not return a file path.")
        return
    payload = api.download(file_path)

    temp_dir = Path(mkdtemp(prefix="anythingintopdfbot-tg-"))
    try:
        result = convert_named_files([(filename, payload)], temp_dir)
        api.send_document(chat_id, result.filename, result.path.read_bytes())
    except ConversionRejected as exc:
        api.send_message(chat_id, exc.detail)
    finally:
        rmtree(temp_dir, ignore_errors=True)


def poll_forever(api: TelegramApi) -> None:
    offset = 0
    while True:
        updates = api.call("getUpdates", {"offset": offset, "timeout": 30, "allowed_updates": ["message"]})
        for update in updates:
            handle_update(update, api)
            offset = int(update["update_id"]) + 1


def main(argv: list[str] | None = None) -> int:
    del argv
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    if not token:
        print("Set TELEGRAM_BOT_TOKEN to run the Telegram bot.", file=sys.stderr)
        return 2
    poll_forever(TelegramApi(token))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
