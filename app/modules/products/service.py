import logging
import os
import shutil

from fastapi import UploadFile

from app.core.uploads import save_uploads
from app.modules.products.domain import Product
from app.modules.products.repository import ProductRepository
from app.modules.products.schemas import ProductCreate, ProductUpdate

logger = logging.getLogger(__name__)


class ProductService:
    def __init__(self, repository: ProductRepository) -> None:
        self.repository = repository

    def list_products(self, only_active: bool = False) -> list[Product]:
        return self.repository.list_all(only_active)

    def get_product(self, product_id: int) -> Product | None:
        return self.repository.get_by_id(product_id)

    def create_product(
        self, data: ProductCreate, photos: list[UploadFile] | None
    ) -> Product:
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
        existing_urls: list[str],
        photos: list[UploadFile] | None,
    ) -> Product | None:
        image_urls = list(existing_urls)
        if photos:
            valid_photos = [p for p in photos if p.filename]
            if valid_photos:
                new_urls = self._save_photos(product_id, valid_photos)
                image_urls.extend(new_urls)

        image_urls = image_urls[:10]

        return self.repository.update(product_id, data, image_urls)

    def reorder_products(self, ordered_ids: list[int]) -> bool:
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

    def _save_photos(self, product_id: int, photos: list[UploadFile]) -> list[str]:
        products_dir = os.path.join(
            os.environ["CONTAINER_MEDIA_PATH"], "products", str(product_id)
        )
        url_prefix = f"/media/products/{product_id}"
        return save_uploads(photos, products_dir, url_prefix)
