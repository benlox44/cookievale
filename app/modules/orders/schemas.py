from pydantic import BaseModel, ConfigDict, Field
from typing import List
from datetime import datetime
from app.modules.orders.domain import OrderStatus


class OrderItemCreate(BaseModel):
    product_id: int
    quantity: int
    unit_price: float


class OrderCreateRequest(BaseModel):
    customer_instagram: str
    delivery_date: datetime
    description: str
    items: List[OrderItemCreate] = Field(min_length=1)
    total_amount: float


class OrderUpdateRequest(BaseModel):
    delivery_date: datetime
    description: str
    amount_paid: float


class OrderResponse(OrderCreateRequest):
    id: int
    status: OrderStatus
    amount_paid: float
    model_config = ConfigDict(from_attributes=True)
