import io
import json
import logging
import os
from datetime import datetime, timedelta

import pytest
from fastapi import UploadFile

from app.core.config import CONTAINER_MEDIA_PATH, TZ
from app.modules.orders import service as order_service_module
from app.modules.orders.domain import DeliveryMethod, Order, OrderItem, OrderStatus
from app.modules.orders.schemas import (
    OrderCreateRequest,
    OrderItemCreate,
    OrderUpdateRequest,
)
from app.modules.orders.service import OrderService

JPEG_MAGIC = b"\xff\xd8\xff\xe0"


class FakeOrderRepository:
    def __init__(self) -> None:
        self._orders: dict[int, Order] = {}
        self._next_id = 1

    def save(self, order: Order) -> Order:
        if order.id is None:
            order.id = self._next_id
            self._next_id += 1
        self._orders[order.id] = order
        return order

    def get_by_id(self, order_id: int) -> Order | None:
        return self._orders.get(order_id)

    def list_all(
        self,
        include_delivered: bool = False,
        limit: int = 100,
        offset: int = 0,
        sort_by: str | None = None,
        sort_dir: str = "desc",
    ) -> list[Order]:
        items = [
            o
            for o in self._orders.values()
            if include_delivered or o.status != OrderStatus.DELIVERED
        ]
        return items[offset : offset + limit]

    def count(self, include_delivered: bool = False) -> int:
        return sum(
            1
            for o in self._orders.values()
            if include_delivered or o.status != OrderStatus.DELIVERED
        )

    def delete(self, order_id: int) -> None:
        self._orders.pop(order_id, None)

    def get_occupied_slot_ids(self) -> set[int]:
        return {
            o.availability_slot_id
            for o in self._orders.values()
            if o.availability_slot_id is not None
        }

    def replace_items(
        self,
        order_id: int,
        items: list[OrderItem],
        total_amount: int,
        amount_paid: int,
    ) -> Order | None:
        order = self._orders.get(order_id)
        if order is None:
            return None
        order.items = items
        order.total_amount = total_amount
        order.amount_paid = amount_paid
        return order


def make_upload(
    content: bytes = JPEG_MAGIC + b"\x00" * 64,
    name: str = "foto.jpg",
    mime: str = "image/jpeg",
) -> UploadFile:
    return UploadFile(
        filename=name, file=io.BytesIO(content), headers={"content-type": mime}
    )


@pytest.fixture
def service() -> OrderService:
    return OrderService(FakeOrderRepository())


def _future_date() -> datetime:
    return datetime.now(tz=TZ) + timedelta(days=2)


def _create_request(amount_paid: int = 0) -> OrderCreateRequest:
    return OrderCreateRequest(
        customer_instagram="@cliente",
        delivery_date=_future_date(),
        availability_slot_id=1,
        description="diseño",
        delivery_method=DeliveryMethod.PICKUP,
        items=[OrderItemCreate(product_id=1, quantity=2, unit_price=1000)],
        total_amount=2000,
    )


def test_create_order_builds_items(service: OrderService) -> None:
    order = service.create_order(_create_request(), [])
    assert order.id is not None
    assert len(order.items) == 1
    assert order.items[0].product_id == 1
    assert order.items[0].quantity == 2
    assert order.amount_paid == 0


def test_create_order_caps_amount_paid(service: OrderService) -> None:
    order = service.create_order(_create_request(), [], amount_paid=9999)
    assert order.amount_paid == 2000


def test_create_order_auto_pays_when_paid(service: OrderService) -> None:
    order = service.create_order(
        _create_request(amount_paid=0), [], status=OrderStatus.PAID
    )
    assert order.amount_paid == 2000


def test_create_order_auto_pays_when_delivered(service: OrderService) -> None:
    order = service.create_order(
        _create_request(amount_paid=0), [], status=OrderStatus.DELIVERED
    )
    assert order.amount_paid == 2000


def test_create_order_saves_photos(service: OrderService) -> None:
    order = service.create_order(_create_request(), [make_upload()])
    assert order.reference_photos
    url = order.reference_photos[0]
    filename = os.path.basename(url)
    saved = os.path.join(CONTAINER_MEDIA_PATH, f"orders/{order.id}", filename)
    assert os.path.isfile(saved)


def test_create_order_without_photos_leaves_empty(service: OrderService) -> None:
    order = service.create_order(_create_request(), [])
    assert order.reference_photos in (None, [])


def test_update_order_items_clamps_amount_paid(service: OrderService) -> None:
    order = service.create_order(_create_request(), [], amount_paid=2000)
    updated = service.update_order_items(
        order.id,
        [OrderItemCreate(product_id=1, quantity=1, unit_price=5000)],
        total_amount=5000,
    )
    assert updated is not None
    assert updated.total_amount == 5000
    assert updated.amount_paid == 2000


def test_update_order_items_auto_pays_when_delivered(service: OrderService) -> None:
    order = service.create_order(_create_request(), [], status=OrderStatus.DELIVERED)
    updated = service.update_order_items(
        order.id,
        [OrderItemCreate(product_id=1, quantity=1, unit_price=5000)],
        total_amount=5000,
    )
    assert updated is not None
    assert updated.amount_paid == 5000


def test_change_status_auto_pays(service: OrderService) -> None:
    order = service.create_order(_create_request(), [])
    updated = service.change_status(order.id, OrderStatus.PAID)
    assert updated is not None
    assert updated.amount_paid == order.total_amount


def test_change_status_keeps_partial_payment(service: OrderService) -> None:
    order = service.create_order(_create_request(), [], amount_paid=500)
    updated = service.change_status(order.id, OrderStatus.CONFIRMED)
    assert updated is not None
    assert updated.amount_paid == 500


def test_update_order_reconciles_photos(service: OrderService) -> None:
    order = service.create_order(_create_request(), [make_upload()])
    existing = order.reference_photos or []
    order_dir = os.path.join(CONTAINER_MEDIA_PATH, f"orders/{order.id}")

    image_order = json.dumps([existing[0], "new:0"])
    updated = service.update_order(
        order.id,
        OrderUpdateRequest(
            delivery_date=order.delivery_date,
            availability_slot_id=1,
            description="nuevo diseño",
            delivery_method=DeliveryMethod.DELIVERY,
            amount_paid=100,
        ),
        existing_photos=existing,
        image_order=image_order,
        photos=[make_upload()],
    )
    assert updated is not None
    assert len(updated.reference_photos or []) == 2
    assert updated.reference_photos[0] == existing[0]
    second = updated.reference_photos[1]
    assert os.path.isfile(os.path.join(order_dir, os.path.basename(second)))


def test_delete_order_removes_media_dir(service: OrderService) -> None:
    order = service.create_order(_create_request(), [make_upload()])
    order_dir = os.path.join(CONTAINER_MEDIA_PATH, f"orders/{order.id}")
    assert os.path.isdir(order_dir)

    service.delete_order(order.id)
    assert not os.path.isdir(order_dir)


def test_update_order_returns_none_for_missing_order(service: OrderService) -> None:
    result = service.update_order(
        999,
        OrderUpdateRequest(
            delivery_date=_future_date(),
            availability_slot_id=None,
            description="x",
            delivery_method=DeliveryMethod.PICKUP,
            amount_paid=0,
        ),
        existing_photos=[],
        image_order="[]",
        photos=None,
    )
    assert result is None


def test_telegram_failure_is_logged_but_order_created(
    service: OrderService,
    caplog: pytest.LogCaptureFixture,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class _RaisingNotifier:
        def __init__(self) -> None:
            pass

        def send_message(self, text: str) -> None:
            raise RuntimeError("telegram down")

    monkeypatch.setattr(order_service_module, "TelegramNotifier", _RaisingNotifier)
    with caplog.at_level(logging.ERROR, logger="app.modules.orders.service"):
        order = service.create_order(_create_request(), [])
    assert order.id is not None
    assert "Failed to send Telegram notification" in caplog.text


def test_change_status_missing_order_returns_none(service: OrderService) -> None:
    assert service.change_status(999, OrderStatus.PAID) is None


def test_update_order_items_missing_order_returns_none(service: OrderService) -> None:
    result = service.update_order_items(
        999, [OrderItemCreate(product_id=1, quantity=1, unit_price=100)], 100
    )
    assert result is None


def test_update_order_deletes_dropped_photos(service: OrderService) -> None:
    order = service.create_order(_create_request(), [make_upload()])
    existing = order.reference_photos or []
    order_dir = os.path.join(CONTAINER_MEDIA_PATH, f"orders/{order.id}")
    dropped_path = os.path.join(order_dir, os.path.basename(existing[0]))
    assert os.path.isfile(dropped_path)

    updated = service.update_order(
        order.id,
        OrderUpdateRequest(
            delivery_date=order.delivery_date,
            availability_slot_id=1,
            description="x",
            delivery_method=DeliveryMethod.PICKUP,
            amount_paid=0,
        ),
        existing_photos=[],
        image_order="[]",
        photos=None,
    )
    assert updated is not None
    assert updated.reference_photos == []
    assert not os.path.isfile(dropped_path)


def test_update_order_logs_warning_on_cleanup_error(
    service: OrderService,
    caplog: pytest.LogCaptureFixture,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    order = service.create_order(_create_request(), [make_upload()])

    def boom(media_dir: str, urls: list[str]) -> None:
        raise OSError("locked")

    monkeypatch.setattr(order_service_module, "delete_media_files", boom)
    with caplog.at_level(logging.WARNING, logger="app.modules.orders.service"):
        updated = service.update_order(
            order.id,
            OrderUpdateRequest(
                delivery_date=order.delivery_date,
                availability_slot_id=1,
                description="x",
                delivery_method=DeliveryMethod.PICKUP,
                amount_paid=0,
            ),
            existing_photos=[],
            image_order="[]",
            photos=None,
        )
    assert updated is not None
    assert "Failed to remove media files for order" in caplog.text
