import json

import pytest
from sqlalchemy.exc import SQLAlchemyError

from app.core.config import BASE_URL


def test_index_renders(client) -> None:
    assert client.get("/").status_code == 200


def test_index_accepts_head(client) -> None:
    assert client.head("/").status_code == 200


def test_health_ok(client) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "connected"}


def test_health_degraded_when_db_down(client, monkeypatch: pytest.MonkeyPatch) -> None:
    from app import main

    class _BrokenEngine:
        def connect(self) -> None:
            raise SQLAlchemyError("down")

    monkeypatch.setattr(main, "engine", _BrokenEngine())
    response = client.get("/health")
    assert response.status_code == 503
    assert response.json() == {"status": "degraded", "database": "unavailable"}


def test_robots_txt(client) -> None:
    response = client.get("/robots.txt")
    assert response.status_code == 200
    assert "User-agent: *" in response.text
    assert "Sitemap:" in response.text


def test_sitemap_xml(client) -> None:
    response = client.get("/sitemap.xml")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/xml")
    assert BASE_URL in response.text
    assert BASE_URL + "/" in response.text
    assert BASE_URL + "/orders/new" in response.text


def test_docs_available_in_debug(client) -> None:
    assert client.get("/docs").status_code == 200


def test_http_request_redirects_to_https(
    client, monkeypatch: pytest.MonkeyPatch
) -> None:
    from app import main

    monkeypatch.setattr(main, "DEBUG", False)
    response = client.get(
        "/", headers={"x-forwarded-proto": "http"}, follow_redirects=False
    )
    assert response.status_code == 301
    assert response.headers["location"].startswith("https://")


def test_admin_form_validation_error_redirects(admin_client) -> None:
    response = admin_client.post(
        "/admin/products",
        data={"name": "", "price": "0", "description": ""},
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert response.headers["location"].startswith("/admin?error=")


def test_admin_validation_error_uses_same_origin_referer(admin_client) -> None:
    response = admin_client.post(
        "/admin/products",
        data={"name": "", "price": "0", "description": ""},
        headers={"referer": "http://testserver/admin/products/7"},
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert response.headers["location"].startswith("/admin/products/7?error=")


def test_admin_validation_error_ignores_external_referer(admin_client) -> None:
    response = admin_client.post(
        "/admin/products",
        data={"name": "", "price": "0", "description": ""},
        headers={"referer": "https://evil.example.com/admin/orders/3"},
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert response.headers["location"].startswith("/admin?error=")


def test_json_validation_error_returns_422(admin_client) -> None:
    response = admin_client.post("/admin/products", json={"bogus": 1})
    assert response.status_code == 422
    assert response.headers["content-type"].startswith("application/json")


def test_rate_limit_with_hx_request_returns_toast(client) -> None:
    data = {
        "customer_instagram": "usuario",
        "cart_items_json": json.dumps([{"product_id": 999, "quantity": 1}]),
        "delivery_date": "2099-01-01T12:00:00",
        "delivery_method": "pickup",
        "description": "d",
    }
    headers = {"HX-Request": "true"}
    for _ in range(5):
        client.post("/orders", data=data, headers=headers)
    response = client.post("/orders", data=data, headers=headers)
    assert response.status_code == 429
    assert "HX-Trigger" in response.headers
    assert "show-toast" in response.headers["HX-Trigger"]
