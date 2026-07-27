from typing import Protocol

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.products.domain import Product
from app.modules.products.models import ProductModel
from app.modules.products.schemas import ProductCreate, ProductUpdate


class ProductRepositoryProtocol(Protocol):
    def list_all(self, only_active: bool = False) -> list[Product]: ...
    def get_by_id(self, product_id: int) -> Product | None: ...
    def create(
        self, data: ProductCreate, image_urls: list[str] | None = None
    ) -> Product: ...
    def update(
        self,
        product_id: int,
        data: ProductUpdate,
        image_urls: list[str] | None = None,
    ) -> Product | None: ...
    def reorder(self, ordered_ids: list[int]) -> bool: ...
    def delete(self, product_id: int) -> bool: ...


class ProductRepository:
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

    def create(
        self, data: ProductCreate, image_urls: list[str] | None = None
    ) -> Product:
        db_product = ProductModel(
            name=data.name,
            description=data.description,
            price=data.price,
            is_active=data.is_active,
            image_urls=image_urls,
        )
        self.db.add(db_product)
        self.db.commit()
        self.db.refresh(db_product)
        return self._to_domain(db_product)

    def update(
        self,
        product_id: int,
        data: ProductUpdate,
        image_urls: list[str] | None = None,
    ) -> Product | None:
        stmt = select(ProductModel).where(ProductModel.id == product_id)
        db_product = self.db.execute(stmt).scalar_one_or_none()
        if not db_product:
            return None

        db_product.name = data.name
        db_product.description = data.description
        db_product.price = data.price
        db_product.is_active = data.is_active
        if image_urls is not None:
            db_product.image_urls = image_urls

        self.db.commit()
        self.db.refresh(db_product)
        return self._to_domain(db_product)

    def reorder(self, ordered_ids: list[int]) -> bool:
        for index, prod_id in enumerate(ordered_ids):
            stmt = select(ProductModel).where(ProductModel.id == prod_id)
            db_product = self.db.execute(stmt).scalar_one_or_none()
            if db_product:
                db_product.display_order = index
        self.db.commit()
        return True

    def delete(self, product_id: int) -> bool:
        stmt = select(ProductModel).where(ProductModel.id == product_id)
        db_product = self.db.execute(stmt).scalar_one_or_none()
        if not db_product:
            return False
        try:
            self.db.delete(db_product)
            self.db.commit()
            return True
        except Exception:
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
