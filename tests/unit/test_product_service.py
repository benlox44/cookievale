import io
import logging
import os

import pytest
from fastapi import UploadFile
from sqlalchemy.exc import SQLAlchemyError

from app.core.config import CONTAINER_MEDIA_PATH, MAX_PRODUCT_IMAGES
from app.modules.products import service as product_service_module
from app.modules.products.domain import Product
from app.modules.products.schemas import ProductInput
from app.modules.products.service import ProductService

JPEG_MAGIC = b"\xff\xd8\xff\xe0"


def make_upload(
    content: bytes = JPEG_MAGIC + b"\x00" * 64,
    name: str = "foto.jpg",
    mime: str = "image/jpeg",
) -> UploadFile:
    return UploadFile(
        filename=name, file=io.BytesIO(content), headers={"content-type": mime}
    )


class FakeProductRepository:
    def __init__(self) -> None:
        self.products: dict[int, Product] = {}
        self._next_id = 1
        self.products_with_orders: set[int] = set()
        self.fail_update = False

    def list_all(self, only_active: bool = False) -> list[Product]:
        return [p for p in self.products.values() if not only_active or p.is_active]

    def get_by_id(self, product_id: int) -> Product | None:
        return self.products.get(product_id)

    def create(self, product: Product, image_urls: list[str] | None = None) -> Product:
        product.id = self._next_id
        self._next_id += 1
        product.image_urls = image_urls
        self.products[product.id] = product
        return product

    def update(
        self,
        product_id: int,
        product: Product,
        image_urls: list[str] | None = None,
    ) -> Product | None:
        if self.fail_update:
            raise SQLAlchemyError("boom")
        current = self.products.get(product_id)
        if current is None:
            return None
        current.name = product.name
        current.price = product.price
        current.description = product.description
        current.is_active = product.is_active
        if image_urls is not None:
            current.image_urls = image_urls
        return current

    def reorder(self, ordered_ids: list[int]) -> bool:
        return True

    def has_orders(self, product_id: int) -> bool:
        return product_id in self.products_with_orders

    def delete(self, product_id: int) -> bool:
        return self.products.pop(product_id, None) is not None


@pytest.fixture
def repo() -> FakeProductRepository:
    return FakeProductRepository()


@pytest.fixture
def service(repo: FakeProductRepository) -> ProductService:
    return ProductService(repo)


def _input(**overrides: object) -> ProductInput:
    data: dict[str, object] = {
        "name": "Galleta",
        "price": 1500,
        "description": "d",
        "is_active": True,
    }
    data.update(overrides)
    return ProductInput(**data)


def test_list_products_passthrough(
    service: ProductService, repo: FakeProductRepository
) -> None:
    repo.create(Product(id=None, name="A", price=1))
    repo.create(Product(id=None, name="B", price=2, is_active=False))
    assert [p.name for p in service.list_products()] == ["A", "B"]
    assert [p.name for p in service.list_products(only_active=True)] == ["A"]


def test_get_product(service: ProductService, repo: FakeProductRepository) -> None:
    product = repo.create(Product(id=None, name="A", price=1))
    assert service.get_product(product.id) is not None
    assert service.get_product(product.id).name == "A"
    assert service.get_product(999) is None


def test_create_product_without_photos(
    service: ProductService, repo: FakeProductRepository
) -> None:
    product = service.create_product(_input(), None)
    assert product.id == 1
    assert repo.products[product.id].name == "Galleta"
    assert product.image_urls is None


def test_create_product_saves_photos(
    service: ProductService, repo: FakeProductRepository
) -> None:
    product = service.create_product(_input(), [make_upload()])
    assert product.image_urls
    url = product.image_urls[0]
    path = os.path.join(
        CONTAINER_MEDIA_PATH, f"products/{product.id}", os.path.basename(url)
    )
    assert os.path.isfile(path)


def test_create_product_caps_photos(service: ProductService) -> None:
    photos = [make_upload(name=f"p{i}.jpg") for i in range(MAX_PRODUCT_IMAGES + 3)]
    product = service.create_product(_input(), photos)
    assert len(product.image_urls or []) == MAX_PRODUCT_IMAGES


def test_create_product_with_invalid_photos_saves_nothing(
    service: ProductService,
) -> None:
    product = service.create_product(_input(), [make_upload(name="")])
    assert product.image_urls in (None, [])


def test_create_product_rolls_back_on_photo_error(
    service: ProductService,
    repo: FakeProductRepository,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def boom(files: list[UploadFile], target_dir: str, url_prefix: str) -> list[str]:
        raise OSError("disk full")

    monkeypatch.setattr(product_service_module, "save_uploads", boom)
    with pytest.raises(OSError):
        service.create_product(_input(), [make_upload()])
    assert repo.products == {}
    product_dir = os.path.join(CONTAINER_MEDIA_PATH, "products", "1")
    assert not os.path.exists(product_dir)


def test_create_product_rolls_back_on_update_error(
    service: ProductService,
    repo: FakeProductRepository,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        product_service_module,
        "save_uploads",
        lambda files, target_dir, url_prefix: ["/media/products/1/x.jpg"],
    )
    repo.fail_update = True
    with pytest.raises(SQLAlchemyError):
        service.create_product(_input(), [make_upload()])
    assert repo.products == {}


def test_update_product_returns_none_for_missing(service: ProductService) -> None:
    result = service.update_product(
        999, _input(), existing_urls=[], image_order="[]", photos=None
    )
    assert result is None


def test_update_product_removes_dropped_media(service: ProductService) -> None:
    product = service.create_product(_input(), [make_upload()])
    url = product.image_urls[0]
    saved = os.path.join(
        CONTAINER_MEDIA_PATH, f"products/{product.id}", os.path.basename(url)
    )
    assert os.path.isfile(saved)

    updated = service.update_product(
        product.id,
        _input(name="Nuevo"),
        existing_urls=[],
        image_order="[]",
        photos=None,
    )
    assert updated is not None
    assert updated.name == "Nuevo"
    assert updated.image_urls == []
    assert not os.path.isfile(saved)


def test_update_product_logs_warning_on_cleanup_error(
    service: ProductService,
    caplog: pytest.LogCaptureFixture,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    product = service.create_product(_input(), [make_upload()])

    def boom(media_dir: str, urls: list[str]) -> None:
        raise OSError("locked")

    monkeypatch.setattr(product_service_module, "delete_media_files", boom)
    with caplog.at_level(logging.WARNING, logger="app.modules.products.service"):
        updated = service.update_product(
            product.id,
            _input(),
            existing_urls=[],
            image_order="[]",
            photos=None,
        )
    assert updated is not None
    assert "Failed to remove media files for product" in caplog.text


def test_reorder_products(service: ProductService) -> None:
    assert service.reorder_products([3, 1, 2]) is True


def test_delete_product_raises_when_has_orders(
    service: ProductService, repo: FakeProductRepository
) -> None:
    product = repo.create(Product(id=None, name="A", price=1))
    repo.products_with_orders.add(product.id)
    with pytest.raises(ValueError):
        service.delete_product(product.id)


def test_delete_product_removes_media_dir(
    service: ProductService, repo: FakeProductRepository
) -> None:
    product = service.create_product(_input(), [make_upload()])
    product_dir = os.path.join(CONTAINER_MEDIA_PATH, f"products/{product.id}")
    assert os.path.isdir(product_dir)

    assert service.delete_product(product.id) is True
    assert not os.path.isdir(product_dir)
    assert repo.products == {}


def test_delete_product_without_media_dir(
    service: ProductService, repo: FakeProductRepository
) -> None:
    product = repo.create(Product(id=None, name="A", price=1))
    assert service.delete_product(product.id) is True
    assert repo.products == {}


def test_delete_product_logs_warning_on_cleanup_error(
    service: ProductService,
    repo: FakeProductRepository,
    caplog: pytest.LogCaptureFixture,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    product = repo.create(Product(id=None, name="A", price=1))
    product_dir = os.path.join(CONTAINER_MEDIA_PATH, f"products/{product.id}")
    os.makedirs(product_dir)

    def boom(path: str) -> None:
        raise OSError("busy")

    monkeypatch.setattr(product_service_module.shutil, "rmtree", boom)
    with caplog.at_level(logging.WARNING, logger="app.modules.products.service"):
        assert service.delete_product(product.id) is True
    assert "Failed to remove media dir for product" in caplog.text
