import json
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.core.config import TZ
from app.modules.orders.domain import OrderStatus
from app.modules.orders.repository import SQLAlchemyOrderRepository
from app.modules.products.repository import SQLAlchemyProductRepository
from app.modules.scheduling.repository import SQLAlchemyAvailabilitySlotRepository


def _future_date(days: int = 2) -> str:
    return (datetime.now(tz=TZ) + timedelta(days=days)).date().isoformat()


def _toast_message(response) -> str:
    return json.loads(response.headers["HX-Trigger"])["show-toast"]["message"]


def test_admin_pages_render(admin_client) -> None:
    for path in [
        "/admin/orders",
        "/admin/orders/new",
        "/admin/products",
        "/admin/products/new",
        "/admin/dates",
    ]:
        assert admin_client.get(path).status_code == 200


def test_create_product(admin_client, db: Session) -> None:
    response = admin_client.post(
        "/admin/products",
        data={
            "name": "Galleta",
            "price": "1500",
            "description": "desc",
            "is_active": "True",
        },
        follow_redirects=False,
    )
    assert response.status_code == 303
    products = SQLAlchemyProductRepository(db).list_all()
    assert len(products) == 1
    assert products[0].name == "Galleta"
    assert products[0].is_active is True


def test_add_slot_rejects_past_date(admin_client, db: Session) -> None:
    past = (datetime.now(tz=TZ) - timedelta(days=1)).date().isoformat()
    response = admin_client.post("/admin/dates", data={"selected_date": past})
    assert response.status_code == 409
    assert SQLAlchemyAvailabilitySlotRepository(db).get_all() == []


def test_order_lifecycle(admin_client, db: Session) -> None:
    admin_client.post(
        "/admin/products",
        data={
            "name": "Galleta",
            "price": "1500",
            "description": "d",
            "is_active": "True",
        },
    )
    product = SQLAlchemyProductRepository(db).list_all()[0]

    date = _future_date()
    assert (
        admin_client.post(
            "/admin/dates", data={"selected_date": date}, follow_redirects=False
        ).status_code
        == 303
    )
    slot = SQLAlchemyAvailabilitySlotRepository(db).get_all()[0]

    cart = json.dumps([{"product_id": product.id, "quantity": 2}])
    response = admin_client.post(
        "/admin/orders",
        data={
            "customer_instagram": "@cliente",
            "cart_items_json": cart,
            "delivery_date": f"{date}T12:00:00",
            "delivery_method": "pickup",
            "description": "diseño",
            "order_status": "pending",
            "amount_paid": "0",
        },
    )
    assert response.status_code == 204
    assert response.headers.get("HX-Redirect") == "/admin/orders"

    order = SQLAlchemyOrderRepository(db).list_all()[0]
    assert order.availability_slot_id == slot.id
    assert order.total_amount == 3000

    assert admin_client.get(f"/admin/orders/{order.id}").status_code == 200

    update = admin_client.post(
        f"/admin/orders/{order.id}",
        data={
            "delivery_date": f"{date}T12:00:00",
            "description": "nuevo diseño",
            "delivery_method": "delivery",
            "amount_paid": "500",
            "status": "confirmed",
            "image_order": "[]",
        },
        follow_redirects=False,
    )
    assert update.status_code == 303

    status = admin_client.post(
        f"/admin/orders/{order.id}/status",
        data={"status": "paid"},
        follow_redirects=False,
    )
    assert status.status_code == 303
    fetched = SQLAlchemyOrderRepository(db).get_by_id(order.id)
    assert fetched is not None
    assert fetched.status == OrderStatus.PAID
    assert fetched.amount_paid == fetched.total_amount

    delete = admin_client.post(
        f"/admin/orders/{order.id}/delete", follow_redirects=False
    )
    assert delete.status_code == 303
    assert SQLAlchemyAvailabilitySlotRepository(db).get_by_id(slot.id) is None
    assert SQLAlchemyOrderRepository(db).get_by_id(order.id) is None


def test_create_order_with_invalid_cart_shows_error(admin_client, db: Session) -> None:
    admin_client.post(
        "/admin/products",
        data={
            "name": "Galleta",
            "price": "1000",
            "description": "d",
            "is_active": "True",
        },
    )
    product = SQLAlchemyProductRepository(db).list_all()[0]
    date = _future_date()
    admin_client.post("/admin/dates", data={"selected_date": date})

    cart = json.dumps([{"product_id": product.id + 999, "quantity": 1}])
    response = admin_client.post(
        "/admin/orders",
        data={
            "customer_instagram": "@cliente",
            "cart_items_json": cart,
            "delivery_date": f"{date}T12:00:00",
            "delivery_method": "pickup",
            "description": "d",
            "order_status": "pending",
            "amount_paid": "0",
        },
    )
    assert response.status_code == 204
    assert "ya no está disponible" in _toast_message(response)


def test_update_order_with_invalid_date_redirects_with_error(
    admin_client, db: Session
) -> None:
    admin_client.post(
        "/admin/products",
        data={
            "name": "Galleta",
            "price": "1000",
            "description": "d",
            "is_active": "True",
        },
    )
    product = SQLAlchemyProductRepository(db).list_all()[0]
    date = _future_date()
    admin_client.post("/admin/dates", data={"selected_date": date})
    cart = json.dumps([{"product_id": product.id, "quantity": 1}])
    admin_client.post(
        "/admin/orders",
        data={
            "customer_instagram": "@cliente",
            "cart_items_json": cart,
            "delivery_date": f"{date}T12:00:00",
            "delivery_method": "pickup",
            "description": "d",
            "order_status": "pending",
            "amount_paid": "0",
        },
    )
    order = SQLAlchemyOrderRepository(db).list_all()[0]

    response = admin_client.post(
        f"/admin/orders/{order.id}",
        data={
            "delivery_date": "no-es-una-fecha",
            "description": "d",
            "delivery_method": "pickup",
            "amount_paid": "0",
            "status": "pending",
            "image_order": "[]",
        },
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert "error=" in response.headers["location"]
