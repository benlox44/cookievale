import json
import logging
import urllib.error
from typing import Self

import pytest

from app.core import telegram
from app.core.config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID


class _FakeResponse:
    def read(self) -> bytes:
        return b"{}"

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *args: object) -> None:
        return None


def test_send_message_posts_payload(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    def fake_urlopen(req: object, timeout: int = 5) -> _FakeResponse:
        captured["url"] = req.full_url
        captured["body"] = json.loads(req.data.decode())
        captured["headers"] = req.headers
        return _FakeResponse()

    monkeypatch.setattr(telegram.urllib.request, "urlopen", fake_urlopen)

    telegram.send_message("Hola")

    assert (
        captured["url"]
        == f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    )
    assert captured["body"] == {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": "Hola",
        "parse_mode": "HTML",
    }
    assert captured["headers"].get("Content-type") == "application/json"


def test_send_message_logs_error_on_urlerror(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    def fake_urlopen(req: object, timeout: int = 5) -> _FakeResponse:
        raise urllib.error.URLError("network down")

    monkeypatch.setattr(telegram.urllib.request, "urlopen", fake_urlopen)

    with caplog.at_level(logging.ERROR, logger="app.core.telegram"):
        telegram.send_message("Hola")

    assert "Failed to send Telegram notification" in caplog.text


def test_send_message_background_spawns_thread(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    spawned: list[object] = []

    class _ImmediateThread:
        def __init__(
            self, target: object, args: tuple[object, ...], daemon: bool
        ) -> None:
            self.target = target
            self.args = args
            self.daemon = daemon

        def start(self) -> None:
            spawned.append(self.daemon)
            if callable(self.target):
                self.target(*self.args)

    monkeypatch.setattr(
        telegram.urllib.request,
        "urlopen",
        lambda req, timeout=5: _FakeResponse(),
    )
    monkeypatch.setattr(telegram.threading, "Thread", _ImmediateThread)

    telegram.send_message("Hola", background=True)
    assert spawned == [True]
