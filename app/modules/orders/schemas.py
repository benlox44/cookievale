from pydantic import BaseModel, ConfigDict, Field, field_validator
from typing import List
from datetime import datetime
from app.modules.orders.domain import OrderStatus, DeliveryMethod


class OrderItemCreate(BaseModel):
    product_id: int = Field(gt=0)
    quantity: int = Field(gt=0)
    unit_price: int = Field(gt=0)


class OrderCreateRequest(BaseModel):
    customer_instagram: str = Field(min_length=1, max_length=100)
    delivery_date: datetime
    description: str = Field(max_length=2000)
    delivery_method: DeliveryMethod
    items: List[OrderItemCreate] = Field(min_length=1)
    total_amount: int = Field(gt=0)

    @field_validator("customer_instagram")
    @classmethod
    def sanitize_instagram(cls, v: str) -> str:
        cleaned = v.strip().lstrip("@")
        if not cleaned:
            raise ValueError("El usuario de Instagram no puede estar vacío.")
        return cleaned


class OrderUpdateRequest(BaseModel):
    delivery_date: datetime
    description: str = Field(max_length=2000)
    delivery_method: DeliveryMethod
    amount_paid: int = Field(ge=0)


class OrderResponse(OrderCreateRequest):
    id: int
    status: OrderStatus
    amount_paid: int
    model_config = ConfigDict(from_attributes=True)
