from typing import List, Optional
from sqlalchemy.orm import Session
from app.modules.products.models import ProductModel
from app.modules.products.schemas import ProductCreate, ProductUpdate


class ProductRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list_all(self, only_active: bool = False) -> List[ProductModel]:
        query = self.db.query(ProductModel)
        if only_active:
            query = query.filter(ProductModel.is_active)
        return query.order_by(ProductModel.id.asc()).all()

    def get_by_id(self, product_id: int) -> Optional[ProductModel]:
        return self.db.query(ProductModel).filter(ProductModel.id == product_id).first()

    def create(
        self, data: ProductCreate, image_urls: Optional[List[str]] = None
    ) -> ProductModel:
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
        return db_product

    def update(
        self,
        product_id: int,
        data: ProductUpdate,
        image_urls: Optional[List[str]] = None,
    ) -> Optional[ProductModel]:
        db_product = self.get_by_id(product_id)
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
        return db_product

    def delete(self, product_id: int) -> bool:
        db_product = self.get_by_id(product_id)
        if not db_product:
            return False
        try:
            self.db.delete(db_product)
            self.db.commit()
            return True
        except Exception:
            self.db.rollback()
            raise
