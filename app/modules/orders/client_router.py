from fastapi import APIRouter, Depends, Request, Form, UploadFile, File, Response
from fastapi.responses import HTMLResponse
from typing import List, Optional
from datetime import datetime
import json

from app.core.templates import templates
from app.core.database import get_db
from sqlalchemy.orm import Session
from app.modules.orders.domain import DeliveryMethod
from app.modules.orders.service import OrderService
from app.modules.orders.schemas import OrderCreateRequest, OrderItemCreate
from app.modules.products.repository import ProductRepository
from app.modules.products.service import ProductService
from app.modules.scheduling.service import SchedulingService
from app.modules.scheduling.repository import AvailableDateRepository
from app.modules.orders.repository import SQLAlchemyOrderRepository

router = APIRouter(prefix="/orders", tags=["Orders"])


def _error_toast(message: str) -> Response:
    headers = {
        "HX-Trigger": json.dumps({"show-toast": {"message": message, "type": "error"}})
    }
    return Response(status_code=204, headers=headers)


def get_product_service(db: Session = Depends(get_db)) -> ProductService:
    return ProductService(ProductRepository(db))


def get_order_service_with_db(db: Session = Depends(get_db)) -> OrderService:
    from app.modules.orders.repository import SQLAlchemyOrderRepository

    return OrderService(SQLAlchemyOrderRepository(db))


@router.get("/new", response_class=HTMLResponse)
def get_new_order_form(
    request: Request,
    product_service: ProductService = Depends(get_product_service),
    db: Session = Depends(get_db),
):
    products = product_service.list_products(only_active=True)
    scheduling_service = SchedulingService(
        AvailableDateRepository(db), SQLAlchemyOrderRepository(db)
    )
    available_dates = scheduling_service.get_available_dates()
    return templates.TemplateResponse(
        request=request,
        name="client/order_form.html",
        context={"products": products, "available_dates": available_dates},
    )


@router.post("")
def submit_order(
    request: Request,
    customer_instagram: str = Form(...),
    cart_items_json: str = Form(...),
    delivery_date: datetime = Form(...),
    delivery_method: DeliveryMethod = Form(...),
    description: str = Form(...),
    photos: Optional[List[UploadFile]] = File(None),
    order_service: OrderService = Depends(get_order_service_with_db),
    product_service: ProductService = Depends(get_product_service),
    db: Session = Depends(get_db),
):
    if photos is None:
        photos = []

    scheduling_service = SchedulingService(
        AvailableDateRepository(db), SQLAlchemyOrderRepository(db)
    )
    available_dates = [d.date for d in scheduling_service.get_available_dates()]
    if delivery_date.date() not in available_dates:
        return _error_toast(
            "La fecha seleccionada ha sido tomada recientemente y no estÃ¡ disponible."
        )

    try:
        cart_items_raw = json.loads(cart_items_json)
    except Exception:
        return _error_toast("Formato de carrito invÃ¡lido.")

    if not cart_items_raw:
        return _error_toast("El carrito no puede estar vacÃ­o.")

    items = []
    total_amount = 0.0

    for item in cart_items_raw:
        prod_id = int(item.get("product_id"))
        qty = int(item.get("quantity"))
        if qty <= 0:
            continue

        product = product_service.get_product(prod_id)
        if not product or not product.is_active:
            return _error_toast("Un producto seleccionado ya no estÃ¡ disponible.")

        unit_p = product.price
        items.append(
            OrderItemCreate(product_id=prod_id, quantity=qty, unit_price=unit_p)
        )
        total_amount += unit_p * qty

    if not items:
        return _error_toast("El carrito no puede estar vacÃ­o.")

    dto = OrderCreateRequest(
        customer_instagram=customer_instagram,
        items=items,
        total_amount=total_amount,
        delivery_date=delivery_date,
        delivery_method=delivery_method,
        description=description,
    )

    order = order_service.create_order(data=dto, photos=photos)

    return templates.TemplateResponse(
        request=request,
        name="client/partials/order_success.html",
        context={"order": order},
    )
