from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class OrderStatus(str, Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    PAID = "paid"
    DELIVERED = "delivered"


FULLY_PAID_STATUSES: frozenset[OrderStatus] = frozenset(
    {OrderStatus.PAID, OrderStatus.DELIVERED}
)


def reconcile_payment(
    status: OrderStatus,
    amount_paid: int,
    total_amount: int,
) -> tuple[OrderStatus, int]:
    """Keep order status and paid amount mutually consistent.

    - PAID/DELIVERED always pay the full total.
    - Otherwise, clamp amount_paid to [0, total_amount]:
      - Full payment (total_amount > 0 and amount_paid >= total_amount) -> PAID.
      - Partial payment (amount_paid > 0) on PENDING -> CONFIRMED.
      - Zero payment keeps PENDING or CONFIRMED as-is.
    """
    if status in FULLY_PAID_STATUSES:
        return status, total_amount
    clamped = max(0, min(amount_paid, total_amount))
    if total_amount > 0 and clamped >= total_amount:
        return OrderStatus.PAID, total_amount
    if clamped > 0 and status == OrderStatus.PENDING:
        return OrderStatus.CONFIRMED, clamped
    return status, clamped


class DeliveryMethod(str, Enum):
    PICKUP = "pickup"
    DELIVERY = "delivery"


@dataclass
class OrderItem:
    product_id: int
    quantity: int
    unit_price: int
    product_name: str | None = None
    id: int | None = None
    order_id: int | None = None


@dataclass
class Order:
    customer_instagram: str
    delivery_date: datetime
    delivery_method: DeliveryMethod
    description: str = ""
    availability_slot_id: int | None = None
    items: list[OrderItem] = field(default_factory=list)
    total_amount: int = 0
    amount_paid: int = 0
    id: int | None = None
    reference_photos: list[str] | None = None
    status: OrderStatus = OrderStatus.PENDING
    created_at: datetime | None = None
