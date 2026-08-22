from typing import Protocol

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.modules.orders.domain import Order, OrderItem, OrderStatus
from app.modules.orders.models import OrderItemModel, OrderModel
from app.modules.products.models import ProductModel


class OrderRepository(Protocol):
    def save(self, order: Order) -> Order: ...
    def get_by_id(self, order_id: int) -> Order | None: ...
    def list_all(
        self,
        include_delivered: bool = False,
        limit: int = 100,
        offset: int = 0,
        sort_by: str | None = None,
        sort_dir: str = "desc",
    ) -> list[Order]: ...
    def count(self, include_delivered: bool = False) -> int: ...
    def delete(self, order_id: int) -> None: ...
    def get_occupied_slot_ids(self) -> set[int]: ...
    def replace_items(
        self,
        order_id: int,
        items: list[OrderItem],
        total_amount: int,
        amount_paid: int,
    ) -> Order | None: ...


class SQLAlchemyOrderRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def _product_names(self, product_ids: set[int]) -> dict[int, str]:
        if not product_ids:
            return {}
        stmt = select(ProductModel.id, ProductModel.name).where(
            ProductModel.id.in_(product_ids)
        )
        return {pid: name for pid, name in self.db.execute(stmt).all()}

    def save(self, order: Order) -> Order:
        names = self._product_names({item.product_id for item in order.items})

        db_items = []
        for item in order.items:
            db_items.append(
                OrderItemModel(
                    id=item.id,
                    product_id=item.product_id,
                    quantity=item.quantity,
                    unit_price=item.unit_price,
                    product_name=names.get(item.product_id),
                )
            )

        db_order = OrderModel(
            id=order.id,
            customer_instagram=order.customer_instagram,
            delivery_date=order.delivery_date,
            availability_slot_id=order.availability_slot_id,
            description=order.description,
            delivery_method=order.delivery_method,
            reference_photos=order.reference_photos,
            status=order.status,
            amount_paid=order.amount_paid,
            total_amount=order.total_amount,
            created_at=order.created_at,
            items=db_items,
        )

        try:
            if order.id is None:
                self.db.add(db_order)
                self.db.flush()
            else:
                db_order = self.db.merge(db_order)
                self.db.flush()
            self.db.commit()
        except IntegrityError:
            self.db.rollback()
            raise ValueError(
                "La fecha seleccionada ya no tiene disponibilidades libres."
            ) from None
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
        include_delivered: bool = False,
        limit: int = 100,
        offset: int = 0,
        sort_by: str | None = None,
        sort_dir: str = "desc",
    ) -> list[Order]:
        stmt = select(OrderModel).options(
            selectinload(OrderModel.items).selectinload(OrderItemModel.product)
        )
        if not include_delivered:
            # Delivered orders are closed: hidden from the default dashboard
            # view and revealed via the "Mostrar entregadas" toggle.
            stmt = stmt.where(OrderModel.status != OrderStatus.DELIVERED)

        if sort_by == "date":
            sort_col = OrderModel.delivery_date
        elif sort_by == "id":
            sort_col = OrderModel.id  # type: ignore[assignment]
        else:
            sort_col = OrderModel.created_at

        stmt = (
            stmt.order_by(sort_col.asc() if sort_dir == "asc" else sort_col.desc())
            .limit(limit)
            .offset(offset)
        )

        db_orders = self.db.execute(stmt).scalars().all()
        return [self._to_domain(o) for o in db_orders]

    def count(self, include_delivered: bool = False) -> int:
        stmt = select(func.count()).select_from(OrderModel)
        if not include_delivered:
            stmt = stmt.where(OrderModel.status != OrderStatus.DELIVERED)
        return self.db.execute(stmt).scalar_one()

    def delete(self, order_id: int) -> None:
        stmt = select(OrderModel).where(OrderModel.id == order_id)
        db_order = self.db.execute(stmt).scalar_one_or_none()
        if db_order:
            self.db.delete(db_order)
            self.db.commit()

    def replace_items(
        self,
        order_id: int,
        items: list[OrderItem],
        total_amount: int,
        amount_paid: int,
    ) -> Order | None:
        stmt = (
            select(OrderModel)
            .where(OrderModel.id == order_id)
            .options(selectinload(OrderModel.items))
        )
        db_order = self.db.execute(stmt).scalar_one_or_none()
        if db_order is None:
            return None

        names = self._product_names({item.product_id for item in items})
        db_order.items.clear()
        for item in items:
            db_order.items.append(
                OrderItemModel(
                    product_id=item.product_id,
                    quantity=item.quantity,
                    unit_price=item.unit_price,
                    product_name=names.get(item.product_id),
                )
            )
        db_order.total_amount = total_amount
        db_order.amount_paid = amount_paid
        self.db.commit()

        return self._to_domain(db_order)

    def get_occupied_slot_ids(self) -> set[int]:
        stmt = select(OrderModel.availability_slot_id)
        return {
            slot_id for slot_id in self.db.scalars(stmt).all() if slot_id is not None
        }

    def _to_domain(self, db_model: OrderModel) -> Order:
        domain_items = []
        for i in db_model.items:
            snapshot = i.product_name
            if not snapshot:
                snapshot = i.product.name if getattr(i, "product", None) else None
            domain_items.append(
                OrderItem(
                    id=i.id,
                    order_id=i.order_id,
                    product_id=i.product_id,
                    quantity=i.quantity,
                    unit_price=i.unit_price,
                    product_name=snapshot or f"Producto {i.product_id}",
                )
            )

        return Order(
            id=db_model.id,
            customer_instagram=db_model.customer_instagram,
            delivery_date=db_model.delivery_date,
            availability_slot_id=db_model.availability_slot_id,
            description=db_model.description,
            delivery_method=db_model.delivery_method,
            reference_photos=db_model.reference_photos,
            status=db_model.status,
            amount_paid=db_model.amount_paid,
            total_amount=db_model.total_amount,
            created_at=db_model.created_at,
            items=domain_items,
        )
