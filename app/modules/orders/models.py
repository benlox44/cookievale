from sqlalchemy import (
    ARRAY,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
)
from sqlalchemy import (
    Enum as SAEnum,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base
from app.modules.orders.domain import DeliveryMethod, OrderStatus


class OrderModel(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)
    customer_instagram = Column(String, nullable=False)
    delivery_date = Column(DateTime, nullable=False)
    description = Column(String, nullable=False)
    delivery_method = Column(
        SAEnum(DeliveryMethod), default=DeliveryMethod.PICKUP, nullable=False
    )

    amount_paid = Column(Integer, default=0, nullable=False)
    total_amount = Column(Integer, default=0, nullable=False)

    reference_photos = Column(ARRAY(String), nullable=True)

    status = Column(SAEnum(OrderStatus), default=OrderStatus.PENDING, nullable=False)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)

    items = relationship(
        "OrderItemModel", back_populates="order", cascade="all, delete-orphan"
    )


class OrderItemModel(Base):
    __tablename__ = "order_items"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    quantity = Column(Integer, nullable=False)
    unit_price = Column(Integer, nullable=False)
    product_name = Column(String(100), nullable=True)

    order = relationship("OrderModel", back_populates="items")
    product = relationship("app.modules.products.models.ProductModel")
