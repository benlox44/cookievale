from datetime import datetime

from sqlalchemy import ARRAY, DateTime, ForeignKey, Index, Integer, String, func, text
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

    # A delivery slot is held by the first active (non-rejected) order on that
    # date; the partial unique index turns the check-then-insert race into a
    # database error instead of a double booking.
    __table_args__ = (
        Index(
            "uq_orders_delivery_date_active",
            func.date(delivery_date),
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
