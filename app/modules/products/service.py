import logging
import os
import shutil

from fastapi import UploadFile
from sqlalchemy.exc import SQLAlchemyError

from app.core.config import CONTAINER_MEDIA_PATH
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

        if product.id is not None and photos:
            valid_photos = [p for p in photos if p.filename][:10]
            if valid_photos:
                product_id = product.id
                try:
                    image_urls = self._save_photos(product_id, valid_photos)
                    update_data = ProductUpdate(
                        name=data.name,
                        price=data.price,
                        description=data.description,
                        is_active=data.is_active,
                    )
                    updated = self.repository.update(
                        product_id, update_data, image_urls
                    )
                    if updated is not None:
                        product = updated
                except (OSError, SQLAlchemyError):
                    self.repository.delete(product_id)
                    product_dir = os.path.join(
                        CONTAINER_MEDIA_PATH, "products", str(product_id)
                    )
                    shutil.rmtree(product_dir, ignore_errors=True)
                    raise

        return product

    def update_product(
        self,
        product_id: int,
        data: ProductUpdate,
        existing_urls: list[str],
        photos: list[UploadFile] | None,
    ) -> Product | None:
        current = self.repository.get_by_id(product_id)
        if current is None:
            return None
        current_urls = current.image_urls or []

        kept = [url for url in existing_urls if url in current_urls]

        if photos:
            valid_photos = [p for p in photos if p.filename]
            if valid_photos:
                remaining = 10 - len(kept)
                if remaining > 0:
                    new_urls = self._save_photos(product_id, valid_photos[:remaining])
                    kept.extend(new_urls)

        final_urls = kept[:10]

        updated = self.repository.update(product_id, data, final_urls)
        if updated is None:
            return None

        removed = [url for url in current_urls if url not in final_urls]
        if removed:
            try:
                self._delete_media_files(product_id, removed)
            except OSError:
                logger.warning(
                    "Failed to remove media files for product %d", product_id
                )

        return updated

    def reorder_products(self, ordered_ids: list[int]) -> bool:
        return self.repository.reorder(ordered_ids)

    def delete_product(self, product_id: int) -> bool:
        if self.repository.has_orders(product_id):
            raise ValueError("No se puede eliminar un producto con pedidos asociados.")
        success = self.repository.delete(product_id)
        if success:
            product_dir = os.path.join(
                CONTAINER_MEDIA_PATH, "products", str(product_id)
            )
            try:
                if os.path.exists(product_dir):
                    shutil.rmtree(product_dir)
            except OSError:
                logger.warning("Failed to remove media dir for product %d", product_id)
        return success

    def _save_photos(self, product_id: int, photos: list[UploadFile]) -> list[str]:
        products_dir = os.path.join(CONTAINER_MEDIA_PATH, "products", str(product_id))
        url_prefix = f"/media/products/{product_id}"
        return save_uploads(photos, products_dir, url_prefix)

    def _delete_media_files(self, product_id: int, urls: list[str]) -> None:
        products_dir = os.path.join(CONTAINER_MEDIA_PATH, "products", str(product_id))
        for url in urls:
            filename = os.path.basename(url)
            if not filename:
                continue
            filepath = os.path.join(products_dir, filename)
            if os.path.isfile(filepath):
                os.remove(filepath)
