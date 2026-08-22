import time

import pytest

from app.core import security
from app.core.config import SESSION_TTL_SECONDS


def test_token_round_trip() -> None:
    token = security.create_admin_token()
    assert security.verify_admin_token(token)


def test_token_rejected_when_expired(monkeypatch: pytest.MonkeyPatch) -> None:
    token = security.create_admin_token()
    now = time.time()
    monkeypatch.setattr(security.time, "time", lambda: now + SESSION_TTL_SECONDS + 1)
    assert not security.verify_admin_token(token)


def test_token_rejected_when_tampered() -> None:
    token = security.create_admin_token()
    tampered = token[:-1] + ("0" if token[-1] != "0" else "1")
    assert not security.verify_admin_token(tampered)


def test_token_rejected_for_malformed_input() -> None:
    assert not security.verify_admin_token("not-a-token")
    assert not security.verify_admin_token("abc:def")
    assert not security.verify_admin_token("")
    assert not security.verify_admin_token(None)  # type: ignore[arg-type]
