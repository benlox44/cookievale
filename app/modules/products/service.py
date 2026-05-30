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
        self, data: ProductCreate, photos: Optional[List[UploadFile]]
    ) -> ProductModel:
        # We first create the product to get its ID for the folder structure
        product = self.repository.create(data, None)

        if photos:
            valid_photos = [p for p in photos if p.filename][:10]
            if valid_photos:
                image_urls = self._save_photos(product.id, valid_photos)
                product = self.repository.update(product.id, data, image_urls)

        return product

    def update_product(
        self,
        product_id: int,
        data: ProductUpdate,
        existing_urls: List[str],
        photos: Optional[List[UploadFile]],
    ) -> Optional[ProductModel]:
        image_urls = list(existing_urls)
        if photos:
            valid_photos = [p for p in photos if p.filename]
            if valid_photos:
                new_urls = self._save_photos(product_id, valid_photos)
                image_urls.extend(new_urls)

        image_urls = image_urls[:10]

        return self.repository.update(product_id, data, image_urls)

    def reorder_products(self, ordered_ids: List[int]) -> bool:
        return self.repository.reorder(ordered_ids)

    def delete_product(self, product_id: int) -> bool:
        success = self.repository.delete(product_id)
        if success:

            product_dir = os.path.join(
                os.environ["CONTAINER_MEDIA_PATH"], "products", str(product_id)
            )
            if os.path.exists(product_dir):
                shutil.rmtree(product_dir)
        return success

    def _save_photos(self, product_id: int, photos: List[UploadFile]) -> List[str]:
        products_dir = os.path.join(
            os.environ["CONTAINER_MEDIA_PATH"], "products", str(product_id)
        )

        os.makedirs(products_dir, exist_ok=True)

        saved_urls = []

        for photo in photos:
            if not photo.filename:
                continue
            ext = photo.filename.split(".")[-1]
            filename = f"{uuid.uuid4().hex}.{ext}"
            filepath = os.path.join(products_dir, filename)

            with open(filepath, "wb") as buffer:
                shutil.copyfileobj(photo.file, buffer)

            saved_urls.append(f"/media/products/{product_id}/{filename}")

        return saved_urls
