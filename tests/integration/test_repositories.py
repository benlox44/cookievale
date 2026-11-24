from datetime import datetime, timedelta

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import TZ
from app.modules.orders.domain import DeliveryMethod, Order, OrderItem, OrderStatus
from app.modules.orders.repository import SQLAlchemyOrderRepository
from app.modules.products.domain import Product
from app.modules.products.repository import SQLAlchemyProductRepository
from app.modules.scheduling.repository import SQLAlchemyAvailabilitySlotRepository


def make_product(db: Session, name: str = "Galleta", price: int = 1000) -> Product:
    repo = SQLAlchemyProductRepository(db)
    return repo.create(Product(id=None, name=name, price=price, is_active=True))


def make_slot(db: Session) -> int:
    repo = SQLAlchemyAvailabilitySlotRepository(db)
    return repo.create(datetime.now(tz=TZ).date() + timedelta(days=2)).id


def make_order(
    db: Session,
    product: Product,
    slot_id: int | None = None,
    status: OrderStatus = OrderStatus.PENDING,
    customer: str = "cliente",
) -> Order:
    order = Order(
        customer_instagram=customer,
        delivery_date=datetime.now(tz=TZ) + timedelta(days=2),
        description="test",
        delivery_method=DeliveryMethod.PICKUP,
        availability_slot_id=slot_id,
        items=[OrderItem(product_id=product.id, quantity=1, unit_price=product.price)],
        total_amount=product.price,
        amount_paid=0,
        status=status,
    )
    return SQLAlchemyOrderRepository(db).save(order)


def test_order_save_assigns_id_and_retrieves(db: Session) -> None:
    product = make_product(db)
    order = make_order(db, product)
    repo = SQLAlchemyOrderRepository(db)

    fetched = repo.get_by_id(order.id)
    assert fetched is not None
    assert fetched.id == order.id
    assert fetched.customer_instagram == "cliente"
    assert fetched.items[0].product_id == product.id
    assert fetched.items[0].product_name == "Galleta"


def test_order_save_rejects_occupied_slot(db: Session) -> None:
    product = make_product(db)
    slot_id = make_slot(db)
    make_order(db, product, slot_id=slot_id)

    with pytest.raises(ValueError):
        make_order(db, product, slot_id=slot_id)


def test_order_save_snapshot_product_name(db: Session) -> None:
    product = make_product(db, name="Original")
    order = make_order(db, product)
    db_product = SQLAlchemyProductRepository(db).get_by_id(product.id)
    assert db_product is not None
    SQLAlchemyProductRepository(db).update(
        db_product.id, Product(id=None, name="Renombrado", price=2000, is_active=True)
    )

    fetched = SQLAlchemyOrderRepository(db).get_by_id(order.id)
    assert fetched is not None
    assert fetched.items[0].product_name == "Original"


def test_order_list_all_excludes_delivered_by_default(db: Session) -> None:
    product = make_product(db)
    make_order(db, product)
    make_order(db, product, status=OrderStatus.DELIVERED)

    repo = SQLAlchemyOrderRepository(db)
    assert len(repo.list_all()) == 1
    assert len(repo.list_all(include_delivered=True)) == 2
    assert repo.count() == 1
    assert repo.count(include_delivered=True) == 2


def test_order_list_all_paginates_and_sorts(db: Session) -> None:
    product = make_product(db)
    for i in range(5):
        make_order(db, product, customer=f"c{i}")

    repo = SQLAlchemyOrderRepository(db)
    page1 = repo.list_all(limit=2, offset=0)
    page2 = repo.list_all(limit=2, offset=2)
    assert len(page1) == 2
    assert len(page2) == 2
    assert {o.id for o in page1} != {o.id for o in page2}


def test_order_delete(db: Session) -> None:
    product = make_product(db)
    order = make_order(db, product)
    repo = SQLAlchemyOrderRepository(db)
    repo.delete(order.id)
    assert repo.get_by_id(order.id) is None


def test_order_replace_items_updates_amounts(db: Session) -> None:
    product = make_product(db)
    order = make_order(db, product, status=OrderStatus.PAID)

    repo = SQLAlchemyOrderRepository(db)
    replaced = repo.replace_items(
        order.id,
        [OrderItem(product_id=product.id, quantity=3, unit_price=500)],
        total_amount=1500,
        amount_paid=1500,
    )
    assert replaced is not None
    assert replaced.total_amount == 1500
    assert replaced.amount_paid == 1500
    assert replaced.items[0].quantity == 3


def test_product_update_and_get(db: Session) -> None:
    product = make_product(db)
    repo = SQLAlchemyProductRepository(db)
    updated = repo.update(
        product.id, Product(id=None, name="Nuevo", price=2500, is_active=False)
    )
    assert updated is not None
    assert updated.name == "Nuevo"
    assert repo.get_by_id(product.id).is_active is False


def test_product_reorder_updates_display_order(db: Session) -> None:
    a = make_product(db, name="A")
    b = make_product(db, name="B")
    repo = SQLAlchemyProductRepository(db)
    assert repo.reorder([b.id, a.id])
    ordered = [p.name for p in repo.list_all()]
    assert ordered[:2] == ["B", "A"]


def test_product_has_orders_and_delete_blocked(db: Session) -> None:
    product = make_product(db)
    make_order(db, product)
    repo = SQLAlchemyProductRepository(db)
    assert repo.has_orders(product.id) is True
    with pytest.raises(IntegrityError):
        repo.delete(product.id)


def test_product_delete_without_orders(db: Session) -> None:
    product = make_product(db)
    repo = SQLAlchemyProductRepository(db)
    assert repo.delete(product.id) is True
    assert repo.get_by_id(product.id) is None


def test_slot_crud_and_purge(db: Session) -> None:
    repo = SQLAlchemyAvailabilitySlotRepository(db)
    today = datetime.now(tz=TZ).date()
    old = repo.create(today - timedelta(days=3))
    kept = repo.create(today + timedelta(days=3))

    assert repo.get_by_id(old.id) is not None
    assert repo.delete_before(today) == 1
    assert repo.get_by_id(old.id) is None
    assert repo.get_by_id(kept.id) is not None

    repo.delete(kept.id)
    assert repo.get_all() == []


def test_order_save_with_no_items(db: Session) -> None:
    order = Order(
        customer_instagram="cliente",
        delivery_date=datetime.now(tz=TZ) + timedelta(days=2),
        description="test",
        delivery_method=DeliveryMethod.PICKUP,
        availability_slot_id=None,
        items=[],
        total_amount=0,
        amount_paid=0,
        status=OrderStatus.PENDING,
    )
    saved = SQLAlchemyOrderRepository(db).save(order)
    assert saved.items == []


def test_order_list_all_sorts_by_id(db: Session) -> None:
    product = make_product(db)
    make_order(db, product, customer="a")
    make_order(db, product, customer="b")

    repo = SQLAlchemyOrderRepository(db)
    ids = [o.id for o in repo.list_all(sort_by="id", sort_dir="asc")]
    assert ids == sorted(ids)


def test_order_replace_items_missing_returns_none(db: Session) -> None:
    assert SQLAlchemyOrderRepository(db).replace_items(999, [], 0, 0) is None


def test_product_update_missing_returns_none(db: Session) -> None:
    repo = SQLAlchemyProductRepository(db)
    assert repo.update(999, Product(id=None, name="x", price=1, is_active=True)) is None


def test_product_update_sets_image_urls(db: Session) -> None:
    product = make_product(db)
    repo = SQLAlchemyProductRepository(db)
    updated = repo.update(
        product.id,
        Product(id=None, name="x", price=1, is_active=True),
        image_urls=["/media/products/1/a.jpg"],
    )
    assert updated is not None
    assert updated.image_urls == ["/media/products/1/a.jpg"]


def test_product_reorder_empty_is_noop(db: Session) -> None:
    assert SQLAlchemyProductRepository(db).reorder([]) is True


def test_product_delete_missing_returns_false(db: Session) -> None:
    assert SQLAlchemyProductRepository(db).delete(999) is False


def test_get_db_yields_working_session_and_closes() -> None:
    from sqlalchemy import text

    from app.core.database import get_db

    gen = get_db()
    session = next(gen)
    try:
        assert session.execute(text("SELECT 1")).scalar() == 1
    finally:
        gen.close()


def test_best_selling_product_id_rules_and_tiebreakers(db: Session) -> None:
    prod_repo = SQLAlchemyProductRepository(db)
    order_repo = SQLAlchemyOrderRepository(db)

    # No sales -> None
    assert order_repo.get_best_selling_product_id() is None

    inactive = prod_repo.create(
        Product(id=None, name="Inactiva", price=5000, is_active=False, display_order=0)
    )
    first = prod_repo.create(
        Product(id=None, name="Primera", price=1000, is_active=True, display_order=1)
    )
    second = prod_repo.create(
        Product(id=None, name="Segunda", price=2000, is_active=True, display_order=2)
    )
    assert inactive.id and first.id and second.id

    def _save(product_id: int, qty: int, price: int, status: OrderStatus) -> None:
        order_repo.save(
            Order(
                customer_instagram="cliente",
                delivery_date=datetime.now(tz=TZ) + timedelta(days=2),
                delivery_method=DeliveryMethod.PICKUP,
                items=[
                    OrderItem(product_id=product_id, quantity=qty, unit_price=price)
                ],
                total_amount=qty * price,
                amount_paid=qty * price
                if status in (OrderStatus.PAID, OrderStatus.DELIVERED)
                else 0,
                status=status,
            )
        )

    # Pending/confirmed and inactive sales are ignored
    _save(first.id, 10, 1000, OrderStatus.PENDING)
    _save(inactive.id, 50, 5000, OrderStatus.DELIVERED)
    assert order_repo.get_best_selling_product_id() is None

    # Tie on units (2 each) AND orders (1 each) -> higher revenue wins (second: 4000 vs first: 2000)
    _save(first.id, 2, 1000, OrderStatus.PAID)
    _save(second.id, 2, 2000, OrderStatus.DELIVERED)
    assert order_repo.get_best_selling_product_id() == second.id

    # Tie on units (4 each) -> more distinct orders wins (first: 3 orders vs second: 2 orders)
    _save(first.id, 1, 1000, OrderStatus.PAID)
    _save(first.id, 1, 1000, OrderStatus.PAID)
    _save(second.id, 2, 2000, OrderStatus.PAID)
    assert order_repo.get_best_selling_product_id() == first.id


def test_suggest_instagrams_ranking_aggregation_and_escaping(db: Session) -> None:
    product = make_product(db)
    repo = SQLAlchemyOrderRepository(db)

    now = datetime.now(tz=TZ)

    def _create(customer: str, minutes_ago: int) -> None:
        repo.save(
            Order(
                customer_instagram=customer,
                delivery_date=now + timedelta(days=2),
                delivery_method=DeliveryMethod.PICKUP,
                items=[
                    OrderItem(
                        product_id=product.id, quantity=1, unit_price=product.price
                    )
                ],
                total_amount=product.price,
                amount_paid=0,
                created_at=now - timedelta(minutes=minutes_ago),
            )
        )

    _create("vale_cookies", minutes_ago=30)
    _create("vale_cookies", minutes_ago=5)
    _create("cookie_vale", minutes_ago=1)
    _create("maria_perez", minutes_ago=10)

    # Empty query returns unique handles ordered by recency with aggregated counts
    recent = repo.suggest_instagrams("")
    assert [s.handle for s in recent] == [
        "cookie_vale",
        "vale_cookies",
        "maria_perez",
    ]
    assert recent[1].order_count == 2

    # Prefix matches rank before substring matches (even when substring is newer),
    # and '@' / uppercase / whitespace are normalized
    matched = repo.suggest_instagrams("  @VALE ")
    assert [(s.handle, s.order_count) for s in matched] == [
        ("vale_cookies", 2),
        ("cookie_vale", 1),
    ]

    # SQL LIKE wildcards ('%' and '_') are escaped literally
    assert repo.suggest_instagrams("%") == []
    assert [s.handle for s in repo.suggest_instagrams("_p")] == ["maria_perez"]

    # Limit is respected
    assert len(repo.suggest_instagrams("", limit=2)) == 2


@pytest.mark.parametrize(
    "invalid_handle",
    ["", "papá", "Abc", ".abc", "abc.", "a..b", "user 1", "a" * 31],
)
def test_order_customer_instagram_db_constraint_rejects_invalid(
    db: Session, invalid_handle: str
) -> None:
    from sqlalchemy.exc import DataError, IntegrityError

    from app.modules.orders.models import OrderModel

    with pytest.raises((IntegrityError, DataError)):
        with db.begin_nested():
            db.add(
                OrderModel(
                    customer_instagram=invalid_handle,
                    delivery_date=datetime.now(tz=TZ) + timedelta(days=2),
                    delivery_method=DeliveryMethod.PICKUP,
                    total_amount=1000,
                    amount_paid=0,
                )
            )
            db.flush()


@pytest.mark.parametrize("valid_handle", ["a", "cookie.vale_1", "a" * 30])
def test_order_customer_instagram_db_constraint_accepts_valid(
    db: Session, valid_handle: str
) -> None:
    product = make_product(db)
    saved = make_order(db, product, customer=valid_handle)
    assert saved.customer_instagram == valid_handle
