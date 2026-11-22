from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from app.modules.orders.domain import DeliveryMethod, OrderStatus


def _clean_instagram(v: str) -> str:
    cleaned = v.strip().lstrip("@").lower()
    if not cleaned:
        raise ValueError("El usuario de Instagram no puede estar vacío.")
    return cleaned


class OrderItemCreate(BaseModel):
    product_id: int = Field(gt=0)
    quantity: int = Field(gt=0, lt=1_000_000_000)
    unit_price: int = Field(gt=0, lt=1_000_000_000)


class OrderCreateRequest(BaseModel):
    customer_instagram: str = Field(min_length=1, max_length=100)
    delivery_date: datetime
    availability_slot_id: int = Field(gt=0)
    description: str = Field(default="", max_length=2000)
    delivery_method: DeliveryMethod
    items: list[OrderItemCreate] = Field(min_length=1)
    total_amount: int = Field(gt=0, lt=1_000_000_000)

    @field_validator("customer_instagram")
    @classmethod
    def sanitize_instagram(cls, v: str) -> str:
        return _clean_instagram(v)


class OrderUpdateRequest(BaseModel):
    delivery_date: datetime
    availability_slot_id: int | None = Field(default=None, gt=0)
    description: str = Field(default="", max_length=2000)
    delivery_method: DeliveryMethod
    amount_paid: int = Field(ge=0, lt=1_000_000_000)
    status: OrderStatus | None = None
    customer_instagram: str | None = Field(default=None, min_length=1, max_length=100)

    @field_validator("customer_instagram")
    @classmethod
    def sanitize_instagram(cls, v: str | None) -> str | None:
        if v is None:
            return None
        return _clean_instagram(v)
