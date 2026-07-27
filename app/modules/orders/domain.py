from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class OrderStatus(str, Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    PAID = "paid"
    DELIVERED = "delivered"
    REJECTED = "rejected"


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
    description: str
    delivery_method: DeliveryMethod
    items: list[OrderItem] = field(default_factory=list)
    total_amount: int = 0
    amount_paid: int = 0
    id: int | None = None
    reference_photos: list[str] | None = None
    status: OrderStatus = OrderStatus.PENDING
    created_at: datetime | None = None
