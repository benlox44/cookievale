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


def test_product_edit_form_404_for_missing(admin_client) -> None:
    assert admin_client.get("/admin/products/999").status_code == 404


def test_update_product(admin_client, db: Session) -> None:
    admin_client.post(
        "/admin/products",
        data={"name": "A", "price": "1000", "description": "d", "is_active": "True"},
    )
    product = SQLAlchemyProductRepository(db).list_all()[0]

    response = admin_client.post(
        f"/admin/products/{product.id}",
        data={
            "name": "B",
            "price": "2000",
            "description": "dd",
            "is_active": "False",
            "existing_images": "[]",
            "image_order": "[]",
        },
        follow_redirects=False,
    )
    assert response.status_code == 303
    fetched = SQLAlchemyProductRepository(db).get_by_id(product.id)
    assert fetched is not None
    assert fetched.name == "B"
    assert fetched.price == 2000
    assert fetched.is_active is False


def test_update_product_missing_redirects(admin_client) -> None:
    response = admin_client.post(
        "/admin/products/999",
        data={
            "name": "B",
            "price": "2000",
            "description": "dd",
            "existing_images": "[]",
            "image_order": "[]",
        },
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert response.headers["location"] == "/admin/products"


def test_product_reorder(admin_client, db: Session) -> None:
    for name in ("A", "B"):
        admin_client.post(
            "/admin/products",
            data={
                "name": name,
                "price": "1000",
                "description": "d",
                "is_active": "True",
            },
        )
    repo = SQLAlchemyProductRepository(db)
    # Default order is display_order asc, id desc → newest (B) first.
    assert [p.name for p in repo.list_all()][:2] == ["B", "A"]

    ids = [p.id for p in repo.list_all()]
    ids.reverse()
    response = admin_client.post("/admin/products/reorder", json={"ordered_ids": ids})
    assert response.status_code == 200
    assert response.json() == {"status": "success"}
    ordered = [p.name for p in repo.list_all()]
    assert ordered[:2] == ["A", "B"]


def test_product_delete_with_orders_redirects_with_error(
    admin_client, db: Session
) -> None:
    admin_client.post(
        "/admin/products",
        data={"name": "A", "price": "1000", "description": "d", "is_active": "True"},
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

    response = admin_client.post(
        f"/admin/products/{product.id}/delete", follow_redirects=False
    )
    assert response.status_code == 303
    assert "error=" in response.headers["location"]
    assert SQLAlchemyProductRepository(db).get_by_id(product.id) is not None


def test_product_delete_without_orders(admin_client, db: Session) -> None:
    admin_client.post(
        "/admin/products",
        data={"name": "A", "price": "1000", "description": "d", "is_active": "True"},
    )
    product = SQLAlchemyProductRepository(db).list_all()[0]

    response = admin_client.post(
        f"/admin/products/{product.id}/delete", follow_redirects=False
    )
    assert response.status_code == 303
    assert SQLAlchemyProductRepository(db).get_by_id(product.id) is None


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


def test_order_detail_404_for_missing(admin_client) -> None:
    assert admin_client.get("/admin/orders/999").status_code == 404


def test_create_order_on_unavailable_date_toast_error(admin_client) -> None:
    response = admin_client.post(
        "/admin/orders",
        data={
            "customer_instagram": "@cliente",
            "cart_items_json": "[]",
            "delivery_date": "2099-01-01T12:00:00",
            "delivery_method": "pickup",
            "description": "d",
            "order_status": "pending",
            "amount_paid": "0",
        },
    )
    assert response.status_code == 204
    assert "no está disponible" in _toast_message(response)


def test_orders_dashboard_renders_partial_for_hx(admin_client, db: Session) -> None:
    response = admin_client.get("/admin/orders", headers={"HX-Request": "true"})
    assert response.status_code == 200
    assert "<table" in response.text
    assert "Crear Orden" not in response.text
    assert "Mostrar entregadas" not in response.text


def test_orders_dashboard_normalizes_sort_params(admin_client) -> None:
    response = admin_client.get(
        "/admin/orders", params={"sort_by": "bogus", "sort_dir": "bogus"}
    )
    assert response.status_code == 200


def test_update_order_with_occupied_date_redirects_with_error(
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
    date1 = _future_date()
    date2 = _future_date(days=3)
    admin_client.post("/admin/dates", data={"selected_date": date1})
    admin_client.post("/admin/dates", data={"selected_date": date2})
    cart = json.dumps([{"product_id": product.id, "quantity": 1}])
    for date in (date1, date2):
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
            "delivery_date": f"{date2}T12:00:00",
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


def test_update_order_to_past_date_succeeds(admin_client, db: Session) -> None:
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
    future = _future_date()
    admin_client.post("/admin/dates", data={"selected_date": future})
    cart = json.dumps([{"product_id": product.id, "quantity": 1}])
    admin_client.post(
        "/admin/orders",
        data={
            "customer_instagram": "@cliente",
            "cart_items_json": cart,
            "delivery_date": f"{future}T12:00:00",
            "delivery_method": "pickup",
            "description": "d",
            "order_status": "pending",
            "amount_paid": "0",
        },
    )
    order = SQLAlchemyOrderRepository(db).list_all()[0]
    past = (datetime.now(tz=TZ) - timedelta(days=1)).date().isoformat()

    response = admin_client.post(
        f"/admin/orders/{order.id}",
        data={
            "delivery_date": f"{past}T12:00:00",
            "description": "d",
            "delivery_method": "pickup",
            "amount_paid": "0",
            "status": "pending",
            "image_order": "[]",
        },
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert response.headers["location"] == "/admin/orders"


def test_update_order_missing_redirects_to_list(admin_client) -> None:
    future = _future_date()
    response = admin_client.post(
        "/admin/orders/999",
        data={
            "delivery_date": f"{future}T12:00:00",
            "description": "d",
            "delivery_method": "pickup",
            "amount_paid": "0",
            "status": "pending",
            "image_order": "[]",
        },
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert response.headers["location"] == "/admin/orders"


def test_order_status_change_surfaces_slot_conflict(admin_client, db: Session) -> None:
    from app.core.dependencies import get_order_service
    from app.main import app

    class _StubOrderService:
        def change_status(self, order_id: int, new_status: OrderStatus) -> None:
            raise ValueError(
                "La fecha seleccionada ya no tiene disponibilidades libres."
            )

    app.dependency_overrides[get_order_service] = lambda: _StubOrderService()
    try:
        response = admin_client.post(
            "/admin/orders/1/status",
            data={"status": "confirmed"},
            follow_redirects=False,
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 303
    assert "error=" in response.headers["location"]


def test_delete_slot_success(admin_client) -> None:
    future = _future_date()
    admin_client.post("/admin/dates", data={"selected_date": future})
    response = admin_client.delete(f"/admin/dates/{future}")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_delete_slot_without_free_slot_returns_409(admin_client, db: Session) -> None:
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
    future = _future_date()
    admin_client.post("/admin/dates", data={"selected_date": future})
    cart = json.dumps([{"product_id": product.id, "quantity": 1}])
    admin_client.post(
        "/admin/orders",
        data={
            "customer_instagram": "@cliente",
            "cart_items_json": cart,
            "delivery_date": f"{future}T12:00:00",
            "delivery_method": "pickup",
            "description": "d",
            "order_status": "pending",
            "amount_paid": "0",
        },
    )

    response = admin_client.delete(f"/admin/dates/{future}")
    assert response.status_code == 409


def test_product_edit_form_renders_for_existing(admin_client, db: Session) -> None:
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
    assert admin_client.get(f"/admin/products/{product.id}").status_code == 200


def _make_order(admin_client, db: Session) -> tuple[int, str]:
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
    cart = json.dumps([{"product_id": product.id, "quantity": 2}])
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
    assert order.id is not None
    return order.id, date


def test_create_order_with_empty_instagram_toast_error(
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

    response = admin_client.post(
        "/admin/orders",
        data={
            "customer_instagram": "@",
            "cart_items_json": cart,
            "delivery_date": f"{date}T12:00:00",
            "delivery_method": "pickup",
            "description": "d",
            "order_status": "pending",
            "amount_paid": "0",
        },
    )
    assert response.status_code == 204
    assert "no puede estar vacío" in _toast_message(response)


def test_update_order_with_cart_items_recomputes_items(
    admin_client, db: Session
) -> None:
    order_id, date = _make_order(admin_client, db)
    cart = json.dumps([{"product_id": _product_id(db), "quantity": 3}])

    response = admin_client.post(
        f"/admin/orders/{order_id}",
        data={
            "delivery_date": f"{date}T12:00:00",
            "description": "d",
            "delivery_method": "pickup",
            "amount_paid": "0",
            "status": "pending",
            "cart_items_json": cart,
            "image_order": "[]",
        },
        follow_redirects=False,
    )
    assert response.status_code == 303
    fetched = SQLAlchemyOrderRepository(db).get_by_id(order_id)
    assert fetched is not None
    assert fetched.items[0].quantity == 3
    assert fetched.total_amount == 3000


def test_update_order_with_invalid_cart_redirects_with_error(
    admin_client, db: Session
) -> None:
    order_id, date = _make_order(admin_client, db)
    cart = json.dumps([{"product_id": 999, "quantity": 1}])

    response = admin_client.post(
        f"/admin/orders/{order_id}",
        data={
            "delivery_date": f"{date}T12:00:00",
            "description": "d",
            "delivery_method": "pickup",
            "amount_paid": "0",
            "status": "pending",
            "cart_items_json": cart,
            "image_order": "[]",
        },
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert "error=" in response.headers["location"]


def test_update_order_to_paid_sets_full_amount(admin_client, db: Session) -> None:
    order_id, date = _make_order(admin_client, db)

    response = admin_client.post(
        f"/admin/orders/{order_id}",
        data={
            "delivery_date": f"{date}T12:00:00",
            "description": "d",
            "delivery_method": "pickup",
            "amount_paid": "0",
            "status": "paid",
            "image_order": "[]",
        },
        follow_redirects=False,
    )
    assert response.status_code == 303
    fetched = SQLAlchemyOrderRepository(db).get_by_id(order_id)
    assert fetched is not None
    assert fetched.status == OrderStatus.PAID
    assert fetched.amount_paid == fetched.total_amount


def _product_id(db: Session) -> int:
    product = SQLAlchemyProductRepository(db).list_all()[0]
    assert product.id is not None
    return product.id
