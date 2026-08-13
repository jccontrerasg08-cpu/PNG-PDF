"""Optional Telegram bot: send a file, get a PDF. No live Telegram network."""

from __future__ import annotations

import json
from io import BytesIO

from fastapi.testclient import TestClient
from PIL import Image

from app.main import app
from app.telegram import TelegramApi, handle_update, main as telegram_main

client = TestClient(app)


def _png() -> bytes:
    buffer = BytesIO()
    Image.new("RGB", (12, 10), (40, 120, 80)).save(buffer, format="PNG")
    return buffer.getvalue()


class FakeResponse:
    def __init__(self, data: bytes) -> None:
        self._data = data

    def read(self) -> bytes:
        return self._data

    def __enter__(self) -> FakeResponse:
        return self

    def __exit__(self, *args: object) -> bool:
        return False


class FakeTelegram:
    def __init__(self, file_bytes: bytes) -> None:
        self.file_bytes = file_bytes
        self.messages: list[str] = []
        self.documents: list[bytes] = []

    def __call__(self, request, timeout=None) -> FakeResponse:
        url = request if isinstance(request, str) else request.full_url
        if "/file/bot" in url:
            return FakeResponse(self.file_bytes)
        if "sendMessage" in url:
            self.messages.append(json.loads(request.data)["text"])
            return FakeResponse(b'{"ok": true, "result": {}}')
        if "sendDocument" in url:
            self.documents.append(request.data)
            return FakeResponse(b'{"ok": true, "result": {}}')
        if "getFile" in url:
            return FakeResponse(
                json.dumps({"ok": True, "result": {"file_path": "documents/photo.png"}}).encode()
            )
        return FakeResponse(b'{"ok": true, "result": {}}')


def test_start_lists_supported_types() -> None:
    transport = FakeTelegram(b"")
    handle_update(
        {"message": {"chat": {"id": 7}, "text": "/start"}},
        TelegramApi("token", opener=transport),
    )
    assert transport.messages
    assert ".png" in transport.messages[0]
    assert "not stored" in transport.messages[0].lower()


def test_document_is_converted_and_sent_as_pdf() -> None:
    transport = FakeTelegram(_png())
    handle_update(
        {
            "message": {
                "chat": {"id": 7},
                "document": {"file_id": "file-1", "file_name": "shot.png"},
            }
        },
        TelegramApi("token", opener=transport),
    )
    assert transport.documents
    assert b"%PDF" in transport.documents[0]


def test_photo_without_filename_becomes_jpg() -> None:
    buffer = BytesIO()
    Image.new("RGB", (12, 10), (200, 80, 40)).save(buffer, format="JPEG")
    transport = FakeTelegram(buffer.getvalue())
    handle_update(
        {
            "message": {
                "chat": {"id": 7},
                "photo": [{"file_id": "small"}, {"file_id": "large"}],
            }
        },
        TelegramApi("token", opener=transport),
    )
    assert transport.documents
    assert b"%PDF" in transport.documents[0]


def test_exe_document_is_rejected_in_chat() -> None:
    transport = FakeTelegram(b"MZ")
    handle_update(
        {
            "message": {
                "chat": {"id": 7},
                "document": {"file_id": "bad", "file_name": "virus.exe"},
            }
        },
        TelegramApi("token", opener=transport),
    )
    assert transport.documents == []
    assert "unsupported" in transport.messages[0].lower()


def test_webhook_without_token_is_404() -> None:
    response = client.post("/telegram/webhook", json={"update_id": 1})
    assert response.status_code == 404


def test_webhook_with_token_converts_document(monkeypatch) -> None:
    transport = FakeTelegram(_png())
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test-token")
    monkeypatch.setattr("app.main.TelegramApi", lambda token: TelegramApi(token, opener=transport))
    response = client.post(
        "/telegram/webhook",
        json={
            "update_id": 1,
            "message": {
                "chat": {"id": 9},
                "document": {"file_id": "file-1", "file_name": "shot.png"},
            },
        },
    )
    assert response.status_code == 200
    assert response.json() == {"ok": True}
    assert transport.documents and b"%PDF" in transport.documents[0]


def test_webhook_rejects_bad_secret(monkeypatch) -> None:
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test-token")
    monkeypatch.setenv("TELEGRAM_WEBHOOK_SECRET", "s3cret")
    response = client.post(
        "/telegram/webhook",
        json={"update_id": 1},
        headers={"X-Telegram-Bot-Api-Secret-Token": "nope"},
    )
    assert response.status_code == 403


def test_polling_main_without_token_exits_2(monkeypatch) -> None:
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    assert telegram_main([]) == 2


def test_homepage_mentions_drop_files() -> None:
    html = client.get("/").text
    assert "drop" in html.lower()
    assert "addEventListener(\"drop\"" in html


def test_homepage_links_telegram_when_username_set(monkeypatch) -> None:
    monkeypatch.setenv("TELEGRAM_BOT_USERNAME", "@MyPdfBot")
    html = client.get("/").text
    assert "https://t.me/MyPdfBot" in html
    assert "@MyPdfBot" in html


def test_homepage_hides_telegram_link_without_username(monkeypatch) -> None:
    monkeypatch.delenv("TELEGRAM_BOT_USERNAME", raising=False)
    html = client.get("/").text
    assert "t.me/" not in html
