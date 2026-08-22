import json
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.core.config import TZ
from app.modules.products.domain import Product
from app.modules.products.repository import SQLAlchemyProductRepository
from app.modules.scheduling.repository import SQLAlchemyAvailabilitySlotRepository


def _setup(client, db: Session, days: int = 3) -> int:
    product = SQLAlchemyProductRepository(db).create(
        Product(id=None, name="Galleta", price=1200, is_active=True)
    )
    slot = SQLAlchemyAvailabilitySlotRepository(db).create(
        (datetime.now(tz=TZ) + timedelta(days=days)).date()
    )
    assert product.id is not None
    return product.id, slot.id


def _payload(
    product_id: int, date: str, cart=None, customer_instagram: str = "usuario"
) -> dict[str, str]:
    return {
        "customer_instagram": customer_instagram,
        "cart_items_json": cart
        or json.dumps([{"product_id": product_id, "quantity": 2}]),
        "delivery_date": f"{date}T12:00:00",
        "delivery_method": "pickup",
        "description": "diseño",
    }


def test_order_form_page_renders(client) -> None:
    assert client.get("/orders/new").status_code == 200


def test_submit_order_success(client, db: Session) -> None:
    product_id, _ = _setup(client, db)
    date = (datetime.now(tz=TZ) + timedelta(days=3)).date().isoformat()

    response = client.post("/orders", data=_payload(product_id, date))
    assert response.status_code == 200
    assert "¡Orden Enviada con Éxito!" in response.text


def _toast_message(response) -> str:
    return json.loads(response.headers["HX-Trigger"])["show-toast"]["message"]


def test_submit_order_with_invalid_cart_toast_error(client, db: Session) -> None:
    product_id, _ = _setup(client, db)
    date = (datetime.now(tz=TZ) + timedelta(days=3)).date().isoformat()

    response = client.post(
        "/orders",
        data=_payload(
            product_id,
            date,
            cart=json.dumps([{"product_id": product_id + 999, "quantity": 1}]),
        ),
    )
    assert response.status_code == 204
    assert "ya no está disponible" in _toast_message(response)


def test_submit_order_on_unavailable_date_toast_error(client, db: Session) -> None:
    product_id, _ = _setup(client, db, days=3)
    date = (datetime.now(tz=TZ) + timedelta(days=30)).date().isoformat()

    response = client.post("/orders", data=_payload(product_id, date))
    assert response.status_code == 204
    assert "no está disponible" in _toast_message(response)


def test_submit_order_is_rate_limited(client, db: Session) -> None:
    product_id, _ = _setup(client, db)
    date = (datetime.now(tz=TZ) + timedelta(days=3)).date().isoformat()
    data = _payload(product_id, date)

    for _ in range(5):
        client.post("/orders", data=data)
    response = client.post("/orders", data=data)
    assert response.status_code == 429


def test_submit_order_with_empty_instagram_toast_error(client, db: Session) -> None:
    product_id, _ = _setup(client, db)
    date = (datetime.now(tz=TZ) + timedelta(days=3)).date().isoformat()

    response = client.post(
        "/orders", data=_payload(product_id, date, customer_instagram="@")
    )
    assert response.status_code == 204
    assert "no puede estar vacío" in _toast_message(response)
