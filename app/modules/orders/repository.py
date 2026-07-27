from typing import Protocol

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.modules.orders.domain import Order, OrderItem, OrderStatus
from app.modules.orders.models import OrderItemModel, OrderModel


class OrderRepository(Protocol):
    def save(self, order: Order) -> Order: ...
    def get_by_id(self, order_id: int) -> Order | None: ...
    def list_all(
        self, status: OrderStatus | None = None, limit: int = 100, offset: int = 0
    ) -> list[Order]: ...
    def delete(self, order_id: int) -> None: ...
    def get_occupied_dates(self) -> set: ...


class SQLAlchemyOrderRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def save(self, order: Order) -> Order:
        db_order = OrderModel(
            id=order.id,
            customer_instagram=order.customer_instagram,
            delivery_date=order.delivery_date,
            description=order.description,
            delivery_method=order.delivery_method,
            reference_photos=order.reference_photos,
            status=order.status,
            amount_paid=order.amount_paid,
            total_amount=order.total_amount,
            created_at=order.created_at,
        )

        db_items = []
        for item in order.items:
            db_item = OrderItemModel(
                id=item.id,
                product_id=item.product_id,
                quantity=item.quantity,
                unit_price=item.unit_price,
            )
            db_items.append(db_item)

        db_order.items = db_items

        if order.id is None:
            self.db.add(db_order)
            self.db.flush()
        else:
            db_order = self.db.merge(db_order)
            self.db.flush()

        self.db.commit()
        self.db.refresh(db_order)

        return self._to_domain(db_order)

    def get_by_id(self, order_id: int) -> Order | None:
        stmt = (
            select(OrderModel)
            .where(OrderModel.id == order_id)
            .options(
                selectinload(OrderModel.items).selectinload(OrderItemModel.product)
            )
        )
        db_order = self.db.execute(stmt).scalar_one_or_none()
        if not db_order:
            return None
        return self._to_domain(db_order)

    def list_all(
        self,
        status: OrderStatus | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Order]:
        stmt = select(OrderModel).options(
            selectinload(OrderModel.items).selectinload(OrderItemModel.product)
        )
        if status is not None:
            stmt = stmt.where(OrderModel.status == status)
        stmt = stmt.order_by(OrderModel.created_at.desc()).limit(limit).offset(offset)

        db_orders = self.db.execute(stmt).scalars().all()
        return [self._to_domain(o) for o in db_orders]

    def delete(self, order_id: int) -> None:
        stmt = select(OrderModel).where(OrderModel.id == order_id)
        db_order = self.db.execute(stmt).scalar_one_or_none()
        if db_order:
            self.db.delete(db_order)
            self.db.commit()

    def get_occupied_dates(self) -> set:
        stmt = select(OrderModel.delivery_date, OrderModel.status).where(
            OrderModel.status != OrderStatus.REJECTED
        )
        rows = self.db.execute(stmt).all()
        return {row.delivery_date.date() for row in rows}

    def _to_domain(self, db_model: OrderModel) -> Order:
        domain_items = []
        for i in db_model.items:
            product_name = (
                i.product.name
                if getattr(i, "product", None)
                else f"Producto {i.product_id}"
            )
            domain_items.append(
                OrderItem(
                    id=i.id,
                    order_id=i.order_id,
                    product_id=i.product_id,
                    quantity=i.quantity,
                    unit_price=i.unit_price,
                    product_name=product_name,
                )
            )

        return Order(
            id=db_model.id,
            customer_instagram=db_model.customer_instagram,
            delivery_date=db_model.delivery_date,
            description=db_model.description,
            delivery_method=db_model.delivery_method,
            reference_photos=db_model.reference_photos,
            status=db_model.status,
            amount_paid=db_model.amount_paid,
            total_amount=db_model.total_amount,
            created_at=db_model.created_at,
            items=domain_items,
        )
