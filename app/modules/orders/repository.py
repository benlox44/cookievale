from datetime import date, datetime, timedelta
from typing import Protocol

from sqlalchemy import case, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.modules.orders.domain import (
    FULLY_PAID_STATUSES,
    InstagramSuggestion,
    Order,
    OrderItem,
    OrderStatus,
    ProductSalesStat,
    SalesStats,
)
from app.modules.orders.models import OrderItemModel, OrderModel
from app.modules.products.models import ProductModel


def _escape_like(value: str) -> str:
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


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
        customer_query: str | None = None,
    ) -> list[Order]: ...
    def count(
        self, include_delivered: bool = False, customer_query: str | None = None
    ) -> int: ...
    def delete(self, order_id: int) -> None: ...
    def get_occupied_slot_ids(self) -> set[int]: ...
    def replace_items(
        self,
        order_id: int,
        items: list[OrderItem],
        total_amount: int,
        amount_paid: int,
    ) -> Order | None: ...
    def get_sales_stats(
        self,
        date_from: date | None = None,
        date_to: date | None = None,
    ) -> SalesStats: ...
    def get_order_date_bounds(self) -> tuple[date | None, date | None]: ...
    def get_best_selling_product_id(self) -> int | None: ...
    def suggest_instagrams(
        self, query: str, limit: int = 8
    ) -> list[InstagramSuggestion]: ...


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

        db_items = [
            OrderItemModel(
                id=item.id,
                product_id=item.product_id,
                quantity=item.quantity,
                unit_price=item.unit_price,
                product_name=names.get(item.product_id),
            )
            for item in order.items
        ]

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
        customer_query: str | None = None,
    ) -> list[Order]:
        stmt = select(OrderModel).options(
            selectinload(OrderModel.items).selectinload(OrderItemModel.product)
        )
        if not include_delivered:
            stmt = stmt.where(OrderModel.status != OrderStatus.DELIVERED)

        cleaned_q = (customer_query or "").strip().lstrip("@").lower()
        if cleaned_q:
            stmt = stmt.where(
                OrderModel.customer_instagram.like(
                    f"%{_escape_like(cleaned_q)}%", escape="\\"
                )
            )

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

    def count(
        self, include_delivered: bool = False, customer_query: str | None = None
    ) -> int:
        stmt = select(func.count()).select_from(OrderModel)
        if not include_delivered:
            stmt = stmt.where(OrderModel.status != OrderStatus.DELIVERED)
        cleaned_q = (customer_query or "").strip().lstrip("@").lower()
        if cleaned_q:
            stmt = stmt.where(
                OrderModel.customer_instagram.like(
                    f"%{_escape_like(cleaned_q)}%", escape="\\"
                )
            )
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

    def get_sales_stats(
        self,
        date_from: date | None = None,
        date_to: date | None = None,
    ) -> SalesStats:
        date_filters = []
        if date_from is not None:
            date_filters.append(
                OrderModel.delivery_date
                >= datetime(date_from.year, date_from.month, date_from.day)
            )
        if date_to is not None:
            next_day = date_to + timedelta(days=1)
            date_filters.append(
                OrderModel.delivery_date
                < datetime(next_day.year, next_day.month, next_day.day)
            )

        completed_statuses = tuple(FULLY_PAID_STATUSES)
        active_paid_statuses = (OrderStatus.CONFIRMED, *completed_statuses)

        summary_stmt = select(
            func.coalesce(
                func.sum(
                    case(
                        (
                            OrderModel.status.in_(completed_statuses),
                            OrderModel.total_amount,
                        ),
                        else_=0,
                    )
                ),
                0,
            ),
            func.coalesce(
                func.sum(
                    case(
                        (
                            OrderModel.status.in_(active_paid_statuses),
                            OrderModel.amount_paid,
                        ),
                        else_=0,
                    )
                ),
                0,
            ),
            func.coalesce(
                func.sum(
                    case(
                        (
                            OrderModel.status == OrderStatus.CONFIRMED,
                            OrderModel.total_amount - OrderModel.amount_paid,
                        ),
                        else_=0,
                    )
                ),
                0,
            ),
            func.coalesce(
                func.sum(case((OrderModel.status.in_(completed_statuses), 1), else_=0)),
                0,
            ),
            func.coalesce(
                func.sum(
                    case((OrderModel.status == OrderStatus.CONFIRMED, 1), else_=0)
                ),
                0,
            ),
        ).where(*date_filters)

        summary_row = self.db.execute(summary_stmt).one()
        completed_revenue = int(summary_row[0])
        collected_amount = int(summary_row[1])
        pending_balance = int(summary_row[2])
        completed_orders = int(summary_row[3])
        confirmed_orders = int(summary_row[4])

        units_expr = func.coalesce(func.sum(OrderItemModel.quantity), 0)
        revenue_expr = func.coalesce(
            func.sum(OrderItemModel.quantity * OrderItemModel.unit_price), 0
        )
        name_expr = func.coalesce(
            ProductModel.name,
            func.max(OrderItemModel.product_name),
            "Producto",
        )

        products_stmt = (
            select(
                OrderItemModel.product_id,
                name_expr,
                units_expr.label("units_sold"),
                func.count(func.distinct(OrderItemModel.order_id)),
                revenue_expr.label("revenue"),
            )
            .join(OrderModel, OrderItemModel.order_id == OrderModel.id)
            .outerjoin(ProductModel, OrderItemModel.product_id == ProductModel.id)
            .where(OrderModel.status.in_(completed_statuses), *date_filters)
            .group_by(OrderItemModel.product_id, ProductModel.name)
            .order_by(
                units_expr.desc(),
                revenue_expr.desc(),
                OrderItemModel.product_id.asc(),
            )
        )

        product_sales = [
            ProductSalesStat(
                product_id=int(row[0]),
                product_name=str(row[1]),
                units_sold=int(row[2]),
                order_count=int(row[3]),
                revenue=int(row[4]),
            )
            for row in self.db.execute(products_stmt).all()
        ]

        return SalesStats(
            completed_revenue=completed_revenue,
            collected_amount=collected_amount,
            pending_balance=pending_balance,
            completed_orders=completed_orders,
            confirmed_orders=confirmed_orders,
            total_units_sold=sum(p.units_sold for p in product_sales),
            product_sales=product_sales,
        )

    def get_order_date_bounds(self) -> tuple[date | None, date | None]:
        active_statuses = (OrderStatus.CONFIRMED, *FULLY_PAID_STATUSES)
        stmt = select(
            func.min(OrderModel.delivery_date),
            func.max(OrderModel.delivery_date),
        ).where(OrderModel.status.in_(active_statuses))
        min_dt, max_dt = self.db.execute(stmt).one()
        return (
            min_dt.date() if min_dt is not None else None,
            max_dt.date() if max_dt is not None else None,
        )

    def get_best_selling_product_id(self) -> int | None:
        completed_statuses = tuple(FULLY_PAID_STATUSES)
        units_expr = func.sum(OrderItemModel.quantity)
        orders_expr = func.count(func.distinct(OrderItemModel.order_id))
        revenue_expr = func.sum(OrderItemModel.quantity * OrderItemModel.unit_price)

        stmt = (
            select(OrderItemModel.product_id)
            .join(OrderModel, OrderItemModel.order_id == OrderModel.id)
            .join(ProductModel, OrderItemModel.product_id == ProductModel.id)
            .where(
                OrderModel.status.in_(completed_statuses),
                ProductModel.is_active.is_(True),
            )
            .group_by(OrderItemModel.product_id, ProductModel.display_order)
            .order_by(
                units_expr.desc(),
                orders_expr.desc(),
                revenue_expr.desc(),
                ProductModel.display_order.asc(),
                OrderItemModel.product_id.asc(),
            )
            .limit(1)
        )
        result = self.db.execute(stmt).scalar_one_or_none()
        return int(result) if result is not None else None

    def suggest_instagrams(
        self, query: str, limit: int = 8
    ) -> list[InstagramSuggestion]:
        cleaned = query.strip().lstrip("@").lower()
        escaped = _escape_like(cleaned)

        last_order_expr = func.max(OrderModel.created_at)
        count_expr = func.count(OrderModel.id)
        stmt = select(
            OrderModel.customer_instagram,
            count_expr.label("order_count"),
        ).group_by(OrderModel.customer_instagram)

        if escaped:
            contains_pattern = f"%{escaped}%"
            prefix_pattern = f"{escaped}%"
            stmt = stmt.where(
                OrderModel.customer_instagram.like(contains_pattern, escape="\\")
            ).order_by(
                case(
                    (
                        OrderModel.customer_instagram.like(prefix_pattern, escape="\\"),
                        0,
                    ),
                    else_=1,
                ).asc(),
                last_order_expr.desc().nullslast(),
                count_expr.desc(),
                OrderModel.customer_instagram.asc(),
            )
        else:
            stmt = stmt.order_by(
                last_order_expr.desc().nullslast(),
                count_expr.desc(),
                OrderModel.customer_instagram.asc(),
            )

        rows = self.db.execute(stmt.limit(limit)).all()
        return [
            InstagramSuggestion(handle=str(row[0]), order_count=int(row[1]))
            for row in rows
        ]

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
