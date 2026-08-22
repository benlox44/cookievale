import os
import tempfile
from collections.abc import Generator
from pathlib import Path

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine, make_url
from sqlalchemy.orm import Session

# App config reads environment variables at import time, so the test settings
# must be in place before any `app.*` module is imported. Tests run against a
# dedicated database and a throwaway media dir so development data is never
# touched.
_DB_URL = make_url(os.environ["DATABASE_URL"])
TEST_DATABASE_URL = _DB_URL.set(database=_DB_URL.database + "_test").render_as_string(
    hide_password=False
)
os.environ["DATABASE_URL"] = TEST_DATABASE_URL
_MEDIA_DIR = Path(tempfile.mkdtemp(prefix="cookievale-test-media-"))
os.environ["CONTAINER_MEDIA_PATH"] = str(_MEDIA_DIR)

from alembic import command
from alembic.config import Config

from app.core.database import engine as app_engine
from app.core.rate_limit import limiter
from app.modules.orders import service as order_service_module


def _ensure_test_database() -> None:
    admin_engine = create_engine(
        _DB_URL.set(database="postgres").render_as_string(hide_password=False),
        isolation_level="AUTOCOMMIT",
    )
    try:
        with admin_engine.connect() as conn:
            exists = conn.execute(
                text("SELECT 1 FROM pg_database WHERE datname = :name"),
                {"name": _DB_URL.database + "_test"},
            ).scalar()
            if not exists:
                conn.execute(text(f'CREATE DATABASE "{_DB_URL.database}_test"'))
    finally:
        admin_engine.dispose()


@pytest.fixture(scope="session", autouse=False)
def db_ready() -> Generator[None, None, None]:
    _ensure_test_database()
    command.upgrade(Config("alembic.ini"), "head")
    yield


@pytest.fixture(scope="session")
def engine() -> Engine:
    return app_engine


@pytest.fixture
def db(db_ready: None, engine: Engine) -> Generator[Session, None, None]:
    connection = engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection, join_transaction_mode="create_savepoint")
    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()


@pytest.fixture
def client(db_ready: None, db: Session):
    from fastapi.testclient import TestClient

    from app.core.database import get_db
    from app.main import app

    def override_get_db() -> Generator[Session, None, None]:
        yield db

    app.dependency_overrides[get_db] = override_get_db
    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.clear()


@pytest.fixture(autouse=True)
def _reset_rate_limiter() -> None:
    limiter.reset()


@pytest.fixture(autouse=True)
def _patch_telegram(monkeypatch: pytest.MonkeyPatch) -> None:
    class _FakeTelegramNotifier:
        def __init__(self) -> None:
            pass

        def send_message(self, text: str) -> None:
            pass

    monkeypatch.setattr(order_service_module, "TelegramNotifier", _FakeTelegramNotifier)


@pytest.fixture
def admin_password() -> str:
    from app.core.config import ADMIN_PASSWORD

    return ADMIN_PASSWORD


@pytest.fixture
def admin_client(client, admin_password: str):
    client.post("/admin/login", data={"password": admin_password})
    return client
