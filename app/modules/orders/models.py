from datetime import datetime

from sqlalchemy import ARRAY, DateTime, ForeignKey, Index, Integer, String, text
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base, TimestampMixin
from app.modules.orders.domain import DeliveryMethod, OrderStatus
from app.modules.products.models import ProductModel


class OrderModel(Base, TimestampMixin):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    customer_instagram: Mapped[str] = mapped_column(String, nullable=False)
    delivery_date: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    availability_slot_id: Mapped[int | None] = mapped_column(
        ForeignKey("availability_slots.id", ondelete="SET NULL"), nullable=True
    )
    description: Mapped[str] = mapped_column(String, nullable=False)
    delivery_method: Mapped[DeliveryMethod] = mapped_column(
        SAEnum(DeliveryMethod), default=DeliveryMethod.PICKUP, nullable=False
    )

    amount_paid: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_amount: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    reference_photos: Mapped[list[str] | None] = mapped_column(
        ARRAY(String), nullable=True
    )

    status: Mapped[OrderStatus] = mapped_column(
        SAEnum(OrderStatus), default=OrderStatus.PENDING, nullable=False
    )

    items: Mapped[list["OrderItemModel"]] = relationship(
        "OrderItemModel", back_populates="order", cascade="all, delete-orphan"
    )

    # A slot can be held by only one active order. The partial unique index
    # protects the final reservation against concurrent submissions.
    __table_args__ = (
        Index(
            "uq_orders_availability_slot_active",
            availability_slot_id,
            unique=True,
            postgresql_where=text("status <> 'REJECTED'"),
        ),
    )


class OrderItemModel(Base, TimestampMixin):
    __tablename__ = "order_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    order_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("orders.id"), nullable=False
    )
    product_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("products.id"), nullable=False
    )
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    unit_price: Mapped[int] = mapped_column(Integer, nullable=False)
    # Historical snapshot of the product name at order time (product can be
    # renamed or deleted afterwards without corrupting the order history).
    product_name: Mapped[str | None] = mapped_column(String(100), nullable=True)

    order: Mapped["OrderModel"] = relationship("OrderModel", back_populates="items")
    product: Mapped[ProductModel] = relationship(ProductModel)
