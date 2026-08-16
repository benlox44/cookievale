from datetime import datetime

from fastapi import APIRouter, Depends, File, Form, Request, Response, UploadFile
from fastapi.responses import HTMLResponse

from app.core.config import TZ
from app.core.dependencies import (
    get_order_service,
    get_product_service,
    get_scheduling_service,
)
from app.core.htmx import error_toast
from app.core.rate_limit import limiter
from app.core.templates import templates
from app.modules.orders.cart import CartError, parse_cart_items
from app.modules.orders.domain import DeliveryMethod
from app.modules.orders.service import OrderService
from app.modules.products.service import ProductService
from app.modules.scheduling.service import SchedulingService

router = APIRouter(prefix="/orders", tags=["Orders"])


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
@limiter.limit("10/hour")
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
        return error_toast(
            "La fecha seleccionada ha sido tomada recientemente y no está disponible."
        )

    try:
        parsed = parse_cart_items(cart_items_json, product_service)
    except CartError as exc:
        return error_toast(exc.message)

    try:
        order = order_service.create_from_parsed_cart(
            cart=parsed,
            customer_instagram=customer_instagram,
            delivery_date=delivery_date,
            delivery_method=delivery_method,
            description=description,
            photos=photos,
        )
    except ValueError as exc:
        return error_toast(str(exc))

    return templates.TemplateResponse(
        request=request,
        name="client/partials/order_success.html",
        context={"order": order},
    )
