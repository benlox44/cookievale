import json

import pytest

from app.modules.orders.cart import CartError, parse_cart_items
from app.modules.products.domain import Product


class FakeProductService:
    def __init__(self, products: list[Product]) -> None:
        self._by_id = {p.id: p for p in products}

    def get_product(self, product_id: int) -> Product | None:
        return self._by_id.get(product_id)


@pytest.fixture
def product_service() -> FakeProductService:
    return FakeProductService(
        [
            Product(id=1, name="Galleta", price=1000, is_active=True),
            Product(id=2, name="Muffin", price=2000, is_active=True),
            Product(id=3, name="Desactivado", price=3000, is_active=False),
        ]
    )


def _cart(payload) -> str:
    return json.dumps(payload)


def test_parse_valid_cart(product_service: FakeProductService) -> None:
    result = parse_cart_items(
        _cart([{"product_id": 1, "quantity": 2}, {"product_id": 2, "quantity": 1}]),
        product_service,
    )
    assert [(i.product_id, i.quantity, i.unit_price) for i in result.items] == [
        (1, 2, 1000),
        (2, 1, 2000),
    ]
    assert result.total_amount == 4000


def test_parse_empty_cart_raises(product_service: FakeProductService) -> None:
    with pytest.raises(CartError):
        parse_cart_items(_cart([]), product_service)


def test_parse_malformed_json_raises(product_service: FakeProductService) -> None:
    with pytest.raises(CartError):
        parse_cart_items("not json", product_service)


def test_parse_bad_item_fields_raises(product_service: FakeProductService) -> None:
    with pytest.raises(CartError):
        parse_cart_items(_cart([{"product_id": "x", "quantity": 1}]), product_service)


def test_parse_skips_non_positive_quantities(
    product_service: FakeProductService,
) -> None:
    with pytest.raises(CartError):
        parse_cart_items(
            _cart(
                [
                    {"product_id": 1, "quantity": 0},
                    {"product_id": 2, "quantity": -3},
                ]
            ),
            product_service,
        )


def test_parse_inactive_product_raises(product_service: FakeProductService) -> None:
    with pytest.raises(CartError):
        parse_cart_items(_cart([{"product_id": 3, "quantity": 1}]), product_service)


def test_parse_unknown_product_raises(product_service: FakeProductService) -> None:
    with pytest.raises(CartError):
        parse_cart_items(_cart([{"product_id": 999, "quantity": 1}]), product_service)


def test_parse_merges_duplicate_product_lines(
    product_service: FakeProductService,
) -> None:
    result = parse_cart_items(
        _cart(
            [
                {"product_id": 1, "quantity": 2},
                {"product_id": 1, "quantity": 3},
            ]
        ),
        product_service,
    )
    assert [(i.product_id, i.quantity) for i in result.items] == [(1, 5)]
    assert result.total_amount == 5000


def test_parse_uses_stored_price_when_given(
    product_service: FakeProductService,
) -> None:
    result = parse_cart_items(
        _cart([{"product_id": 2, "quantity": 1}]),
        product_service,
        stored_prices={2: 500},
    )
    assert result.items[0].unit_price == 500
    assert result.total_amount == 500
