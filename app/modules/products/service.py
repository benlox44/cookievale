import os
import shutil
import uuid
from typing import List, Optional
from fastapi import UploadFile

from app.modules.products.models import ProductModel
from app.modules.products.schemas import ProductCreate, ProductUpdate
from app.modules.products.repository import ProductRepository


class ProductService:
    def __init__(self, repository: ProductRepository) -> None:
        self.repository = repository

    def list_products(self, only_active: bool = False) -> List[ProductModel]:
        return self.repository.list_all(only_active)

    def get_product(self, product_id: int) -> Optional[ProductModel]:
        return self.repository.get_by_id(product_id)

    def create_product(
        self, data: ProductCreate, photo: Optional[UploadFile]
    ) -> ProductModel:
        image_url = None
        if photo and photo.filename:
            image_url = self._save_photo(photo)

        return self.repository.create(data, image_url)

    def update_product(
        self, product_id: int, data: ProductUpdate, photo: Optional[UploadFile]
    ) -> Optional[ProductModel]:
        image_url = None
        if photo and photo.filename:
            image_url = self._save_photo(photo)

        return self.repository.update(product_id, data, image_url)

    def delete_product(self, product_id: int) -> bool:
        return self.repository.delete(product_id)

    def _save_photo(self, photo: UploadFile) -> str:
        products_dir = os.path.join(os.environ["CONTAINER_MEDIA_PATH"], "products")
        os.makedirs(products_dir, exist_ok=True)

        ext = photo.filename.split(".")[-1]
        filename = f"{uuid.uuid4().hex}.{ext}"
        filepath = os.path.join(products_dir, filename)

        with open(filepath, "wb") as buffer:
            shutil.copyfileobj(photo.file, buffer)

        return f"/media/products/{filename}"
