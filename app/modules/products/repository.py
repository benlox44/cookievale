from typing import Protocol

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.modules.orders.models import OrderItemModel
from app.modules.products.domain import Product
from app.modules.products.models import ProductModel


class ProductRepository(Protocol):
    def list_all(self, only_active: bool = False) -> list[Product]: ...
    def get_by_id(self, product_id: int) -> Product | None: ...
    def create(
        self, product: Product, image_urls: list[str] | None = None
    ) -> Product: ...
    def update(
        self,
        product_id: int,
        product: Product,
        image_urls: list[str] | None = None,
    ) -> Product | None: ...
    def reorder(self, ordered_ids: list[int]) -> bool: ...
    def has_orders(self, product_id: int) -> bool: ...
    def delete(self, product_id: int) -> bool: ...


class SQLAlchemyProductRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list_all(self, only_active: bool = False) -> list[Product]:
        stmt = select(ProductModel)
        if only_active:
            stmt = stmt.where(ProductModel.is_active)
        stmt = stmt.order_by(ProductModel.display_order.asc(), ProductModel.id.desc())
        models = self.db.execute(stmt).scalars().all()
        return [self._to_domain(m) for m in models]

    def get_by_id(self, product_id: int) -> Product | None:
        stmt = select(ProductModel).where(ProductModel.id == product_id)
        model = self.db.execute(stmt).scalar_one_or_none()
        if model is None:
            return None
        return self._to_domain(model)

    def create(self, product: Product, image_urls: list[str] | None = None) -> Product:
        db_product = ProductModel(
            name=product.name,
            description=product.description,
            price=product.price,
            is_active=product.is_active,
            image_urls=image_urls,
        )
        self.db.add(db_product)
        self.db.commit()
        self.db.refresh(db_product)
        return self._to_domain(db_product)

    def update(
        self,
        product_id: int,
        product: Product,
        image_urls: list[str] | None = None,
    ) -> Product | None:
        stmt = select(ProductModel).where(ProductModel.id == product_id)
        db_product = self.db.execute(stmt).scalar_one_or_none()
        if not db_product:
            return None

        db_product.name = product.name
        db_product.description = product.description
        db_product.price = product.price
        db_product.is_active = product.is_active
        if image_urls is not None:
            db_product.image_urls = image_urls

        self.db.commit()
        self.db.refresh(db_product)
        return self._to_domain(db_product)

    def reorder(self, ordered_ids: list[int]) -> bool:
        if not ordered_ids:
            return True
        # Single round-trip instead of one SELECT per product.
        models = (
            self.db.execute(
                select(ProductModel).where(ProductModel.id.in_(ordered_ids))
            )
            .scalars()
            .all()
        )
        by_id = {m.id: m for m in models}
        ordered = {pid: index for index, pid in enumerate(ordered_ids)}
        for pid, index in ordered.items():
            model = by_id.get(pid)
            if model is not None:
                model.display_order = index
        self.db.commit()
        return True

    def has_orders(self, product_id: int) -> bool:
        stmt = (
            select(OrderItemModel.id)
            .where(OrderItemModel.product_id == product_id)
            .limit(1)
        )
        return self.db.execute(stmt).scalars().first() is not None

    def delete(self, product_id: int) -> bool:
        stmt = select(ProductModel).where(ProductModel.id == product_id)
        db_product = self.db.execute(stmt).scalar_one_or_none()
        if not db_product:
            return False
        try:
            self.db.delete(db_product)
            self.db.commit()
            return True
        except SQLAlchemyError:
            self.db.rollback()
            raise

    def _to_domain(self, model: ProductModel) -> Product:
        return Product(
            id=model.id,
            name=model.name,
            price=model.price,
            description=model.description,
            is_active=model.is_active,
            image_urls=model.image_urls,
            display_order=model.display_order,
        )
