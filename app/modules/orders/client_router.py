from fastapi import APIRouter, Depends, Request, Form, UploadFile, File, HTTPException
from fastapi.responses import HTMLResponse
from typing import List
from datetime import datetime
import json

from app.core.templates import templates
from app.core.database import get_db
from sqlalchemy.orm import Session
from app.modules.orders.service import OrderService
from app.modules.orders.schemas import OrderCreateRequest, OrderItemCreate
from app.modules.products.repository import ProductRepository
from app.modules.products.service import ProductService

router = APIRouter(prefix="/orders", tags=["Orders"])


def get_product_service(db: Session = Depends(get_db)) -> ProductService:
    return ProductService(ProductRepository(db))


def get_order_service_with_db(db: Session = Depends(get_db)) -> OrderService:
    from app.modules.orders.repository import SQLAlchemyOrderRepository

    return OrderService(SQLAlchemyOrderRepository(db))


@router.get("/new", response_class=HTMLResponse)
def get_new_order_form(
    request: Request, product_service: ProductService = Depends(get_product_service)
):
    products = product_service.list_products(only_active=True)
    return templates.TemplateResponse(
        request=request, name="client/form.html", context={"products": products}
    )


@router.post("")
def submit_order(
    request: Request,
    customer_instagram: str = Form(...),
    cart_items_json: str = Form(...),
    delivery_date: datetime = Form(...),
    description: str = Form(...),
    photos: List[UploadFile] = File(default=[]),
    order_service: OrderService = Depends(get_order_service_with_db),
    product_service: ProductService = Depends(get_product_service),
):
    try:
        cart_items_raw = json.loads(cart_items_json)
    except Exception:
        raise HTTPException(status_code=400, detail="Formato de carrito inválido")

    if not cart_items_raw:
        raise HTTPException(status_code=400, detail="El carrito no puede estar vacío")

    items = []
    total_amount = 0.0

    for item in cart_items_raw:
        prod_id = int(item.get("product_id"))
        qty = int(item.get("quantity"))
        if qty <= 0:
            continue

        product = product_service.get_product(prod_id)
        if not product or not product.is_active:
            raise HTTPException(
                status_code=400,
                detail=f"El producto con ID {prod_id} no está disponible",
            )

        unit_p = product.price
        items.append(
            OrderItemCreate(product_id=prod_id, quantity=qty, unit_price=unit_p)
        )
        total_amount += unit_p * qty

    if not items:
        raise HTTPException(status_code=400, detail="El carrito no puede estar vacío")

    dto = OrderCreateRequest(
        customer_instagram=customer_instagram,
        items=items,
        total_amount=total_amount,
        delivery_date=delivery_date,
        description=description,
    )

    order = order_service.create_order(data=dto, photos=photos)

    return templates.TemplateResponse(
        request=request,
        name="client/partials/order_success.html",
        context={"order": order},
    )
