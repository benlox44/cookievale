import json
from datetime import datetime

from fastapi import APIRouter, Depends, File, Form, Request, Response, UploadFile
from fastapi.responses import HTMLResponse

from app.core.config import TZ
from app.core.dependencies import (
    get_order_service,
    get_product_service,
    get_scheduling_service,
)
from app.core.templates import templates
from app.modules.orders.cart import CartError, parse_cart_items
from app.modules.orders.domain import DeliveryMethod
from app.modules.orders.schemas import OrderCreateRequest
from app.modules.orders.service import OrderService
from app.modules.products.service import ProductService
from app.modules.scheduling.service import SchedulingService

router = APIRouter(prefix="/orders", tags=["Orders"])


def _error_toast(message: str) -> Response:
    headers = {
        "HX-Trigger": json.dumps({"show-toast": {"message": message, "type": "error"}})
    }
    return Response(status_code=204, headers=headers)


@router.get("/new", response_class=HTMLResponse)
def get_new_order_form(
    request: Request,
    product_service: ProductService = Depends(get_product_service),
    scheduling_service: SchedulingService = Depends(get_scheduling_service),
) -> HTMLResponse:
    products = product_service.list_products(only_active=True)
    available_dates = scheduling_service.get_available_dates()
    return templates.TemplateResponse(
        request=request,
        name="client/order_form.html",
        context={
            "products": products,
            "available_dates": available_dates,
            "today": datetime.now(tz=TZ).date().strftime("%Y-%m-%d"),
        },
    )


@router.post("")
def submit_order(
    request: Request,
    customer_instagram: str = Form(...),
    cart_items_json: str = Form(...),
    delivery_date: datetime = Form(...),
    delivery_method: DeliveryMethod = Form(...),
    description: str = Form(...),
    photos: list[UploadFile] | None = File(None),
    order_service: OrderService = Depends(get_order_service),
    product_service: ProductService = Depends(get_product_service),
    scheduling_service: SchedulingService = Depends(get_scheduling_service),
) -> Response:
    if photos is None:
        photos = []

    available_dates = [d.date for d in scheduling_service.get_available_dates()]
    if delivery_date.date() not in available_dates:
        return _error_toast(
            "La fecha seleccionada ha sido tomada recientemente y no está disponible."
        )

    try:
        parsed = parse_cart_items(cart_items_json, product_service)
    except CartError as exc:
        return _error_toast(exc.message)

    dto = OrderCreateRequest(
        customer_instagram=customer_instagram,
        items=parsed.items,
        total_amount=parsed.total_amount,
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
