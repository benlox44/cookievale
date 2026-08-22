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
