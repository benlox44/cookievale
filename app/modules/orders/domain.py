from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from enum import Enum


class OrderStatus(str, Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    PAID = "paid"
    DELIVERED = "delivered"


FULLY_PAID_STATUSES: frozenset[OrderStatus] = frozenset(
    {OrderStatus.PAID, OrderStatus.DELIVERED}
)


def reconcile_payment(
    status: OrderStatus,
    amount_paid: int,
    total_amount: int,
) -> tuple[OrderStatus, int]:
    """Keep order status and paid amount mutually consistent.

    - PAID/DELIVERED always pay the full total.
    - Otherwise, clamp amount_paid to [0, total_amount]:
      - Full payment (total_amount > 0 and amount_paid >= total_amount) -> PAID.
      - Partial payment (amount_paid > 0) on PENDING -> CONFIRMED.
      - Zero payment keeps PENDING or CONFIRMED as-is.
    """
    if status in FULLY_PAID_STATUSES:
        return status, total_amount
    clamped = max(0, min(amount_paid, total_amount))
    if total_amount > 0 and clamped >= total_amount:
        return OrderStatus.PAID, total_amount
    if clamped > 0 and status == OrderStatus.PENDING:
        return OrderStatus.CONFIRMED, clamped
    return status, clamped


class DeliveryMethod(str, Enum):
    PICKUP = "pickup"
    DELIVERY = "delivery"


@dataclass
class OrderItem:
    product_id: int
    quantity: int
    unit_price: int
    product_name: str | None = None
    id: int | None = None
    order_id: int | None = None


@dataclass
class Order:
    customer_instagram: str
    delivery_date: datetime
    delivery_method: DeliveryMethod
    description: str = ""
    availability_slot_id: int | None = None
    items: list[OrderItem] = field(default_factory=list)
    total_amount: int = 0
    amount_paid: int = 0
    id: int | None = None
    reference_photos: list[str] | None = None
    status: OrderStatus = OrderStatus.PENDING
    created_at: datetime | None = None


@dataclass
class ProductSalesStat:
    product_id: int
    product_name: str
    units_sold: int
    order_count: int
    revenue: int


@dataclass
class SalesStats:
    completed_revenue: int = 0
    collected_amount: int = 0
    pending_balance: int = 0
    completed_orders: int = 0
    confirmed_orders: int = 0
    total_units_sold: int = 0
    product_sales: list[ProductSalesStat] = field(default_factory=list)

    @property
    def average_ticket(self) -> int:
        if self.completed_orders == 0:
            return 0
        return self.completed_revenue // self.completed_orders


_WEEKDAYS_SHORT = ("Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom")
_MONTHS_SHORT = (
    "Ene",
    "Feb",
    "Mar",
    "Abr",
    "May",
    "Jun",
    "Jul",
    "Ago",
    "Sep",
    "Oct",
    "Nov",
    "Dic",
)


def _fmt_short_date(d: date) -> str:
    return f"{d.day} {_MONTHS_SHORT[d.month - 1]}"


def _fmt_day_heading(d: date) -> str:
    return f"{_WEEKDAYS_SHORT[d.weekday()]} {_fmt_short_date(d)}"


@dataclass
class ProductionProductTotal:
    product_id: int
    product_name: str
    quantity: int


@dataclass
class ProductionDay:
    date: date
    label: str
    orders: list[Order]
    product_totals: list[ProductionProductTotal]


@dataclass
class ProductionWeek:
    week_start: date
    week_end: date
    title: str
    days: list[ProductionDay]
    product_totals: list[ProductionProductTotal]
    pending_days: list[ProductionDay] = field(default_factory=list)
    pending_totals: list[ProductionProductTotal] = field(default_factory=list)


def _aggregate_products(orders: list[Order]) -> list[ProductionProductTotal]:
    totals: dict[int, ProductionProductTotal] = {}
    for order in orders:
        for item in order.items:
            name = item.product_name or f"Producto {item.product_id}"
            existing = totals.get(item.product_id)
            if existing is None:
                totals[item.product_id] = ProductionProductTotal(
                    product_id=item.product_id,
                    product_name=name,
                    quantity=item.quantity,
                )
            else:
                existing.quantity += item.quantity
    return sorted(
        totals.values(),
        key=lambda t: (-t.quantity, t.product_name.lower(), t.product_id),
    )


def build_production_schedule(orders: list[Order]) -> list[ProductionWeek]:
    active_orders = [o for o in orders if o.status != OrderStatus.DELIVERED]
    active_orders.sort(key=lambda o: (o.delivery_date.date(), o.id or 0))

    by_week: dict[date, dict[date, list[Order]]] = {}
    for order in active_orders:
        day_date = order.delivery_date.date()
        monday = day_date - timedelta(days=day_date.weekday())
        by_week.setdefault(monday, {}).setdefault(day_date, []).append(order)

    weeks: list[ProductionWeek] = []
    for monday, days_map in by_week.items():
        sunday = monday + timedelta(days=6)
        confirmed_days: list[ProductionDay] = []
        pending_days: list[ProductionDay] = []

        for day_date, day_orders in days_map.items():
            confirmed = [
                o
                for o in day_orders
                if o.status in (OrderStatus.CONFIRMED, OrderStatus.PAID)
            ]
            pending = [o for o in day_orders if o.status == OrderStatus.PENDING]

            if confirmed:
                confirmed_days.append(
                    ProductionDay(
                        date=day_date,
                        label=_fmt_day_heading(day_date),
                        orders=confirmed,
                        product_totals=_aggregate_products(confirmed),
                    )
                )
            if pending:
                pending_days.append(
                    ProductionDay(
                        date=day_date,
                        label=_fmt_day_heading(day_date),
                        orders=pending,
                        product_totals=_aggregate_products(pending),
                    )
                )

        week_confirmed = [o for d in confirmed_days for o in d.orders]
        week_pending = [o for d in pending_days for o in d.orders]

        weeks.append(
            ProductionWeek(
                week_start=monday,
                week_end=sunday,
                title=f"Semana {_fmt_short_date(monday)} – {_fmt_short_date(sunday)}",
                days=confirmed_days,
                product_totals=_aggregate_products(week_confirmed),
                pending_days=pending_days,
                pending_totals=_aggregate_products(week_pending),
            )
        )

    return weeks
