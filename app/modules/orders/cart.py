import json
from dataclasses import dataclass

from app.modules.orders.schemas import OrderItemCreate
from app.modules.products.service import ProductService


class CartError(Exception):
    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


@dataclass(frozen=True)
class ParsedCart:
    items: list[OrderItemCreate]
    total_amount: int


def parse_cart_items(
    cart_json: str,
    product_service: ProductService,
    stored_prices: dict[int, int] | None = None,
) -> ParsedCart:
    """Parse and validate the cart JSON sent by the order forms.

    Reused by the client submission, the admin creation and the cart edit
    endpoint so the validation rules stay in a single place. Raises CartError
    with a user-facing message when the cart is invalid.

    stored_prices maps product_id -> unit_price for items already present in
    an order (used by the cart editor). Existing items keep their price
    snapshot even if the product was deactivated afterwards; only items not
    already in the order are required to be active and use the current price.
    """
    try:
        cart_raw = json.loads(cart_json)
    except json.JSONDecodeError as exc:
        raise CartError("Formato de carrito inválido.") from exc

    if not cart_raw:
        raise CartError("El carrito no puede estar vacío.")

    items: list[OrderItemCreate] = []
    total = 0
    for item in cart_raw:
        try:
            prod_id = int(item.get("product_id"))
            qty = int(item.get("quantity"))
        except (TypeError, ValueError) as exc:
            raise CartError("Formato de carrito inválido.") from exc
        if qty <= 0:
            continue

        stored = (stored_prices or {}).get(prod_id)
        if stored is not None:
            unit_p = stored
        else:
            product = product_service.get_product(prod_id)
            if not product or not product.is_active:
                raise CartError("Un producto seleccionado ya no está disponible.")
            unit_p = product.price

        items.append(
            OrderItemCreate(product_id=prod_id, quantity=qty, unit_price=unit_p)
        )
        total += unit_p * qty

    if not items:
        raise CartError("El carrito no puede estar vacío.")

    return ParsedCart(items=items, total_amount=total)
