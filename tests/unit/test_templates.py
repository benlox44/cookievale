from datetime import date

from app.core.templates import (
    clp,
    date_short,
    delivery_label,
    status_label,
)
from app.modules.orders.domain import DeliveryMethod, OrderStatus


def test_clp_formats_with_separators() -> None:
    assert clp(1000) == "$1,000"
    assert clp(1234567) == "$1,234,567"
    assert clp(0) == "$0"


def test_status_label_from_enum() -> None:
    assert status_label(OrderStatus.PENDING) == "Pendiente"
    assert status_label(OrderStatus.DELIVERED) == "Entregada"


def test_status_label_from_string() -> None:
    assert status_label("paid") == "Pagada"
    assert status_label("desconocido") == "desconocido"


def test_delivery_label_from_enum() -> None:
    assert delivery_label(DeliveryMethod.PICKUP) == "Retiro"
    assert delivery_label(DeliveryMethod.DELIVERY) == "Delivery"


def test_date_short_in_spanish() -> None:
    assert date_short(date(2026, 8, 21)) == "vie-21-ago-2026"
    assert date_short(date(2026, 1, 1)) == "jue-01-ene-2026"
    assert date_short(date(2026, 12, 31)) == "jue-31-dic-2026"
