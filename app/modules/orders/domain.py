from enum import Enum
from dataclasses import dataclass, field
from typing import List, Optional
from datetime import datetime


class OrderStatus(str, Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    PAID = "paid"
    DELIVERED = "delivered"
    REJECTED = "rejected"


@dataclass
class OrderItem:
    product_id: int
    quantity: int
    unit_price: float
    product_name: Optional[str] = None
    id: Optional[int] = None
    order_id: Optional[int] = None


@dataclass
class Order:
    customer_instagram: str
    delivery_date: datetime
    description: str
    items: List[OrderItem] = field(default_factory=list)
    total_amount: float = 0.0
    amount_paid: float = 0.0
    id: Optional[int] = None
    reference_photos: Optional[List[str]] = None
    status: OrderStatus = OrderStatus.PENDING
    created_at: Optional[datetime] = None
