import json
from datetime import datetime

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    Request,
    Response,
    UploadFile,
    status,
)
from fastapi.responses import HTMLResponse, RedirectResponse

from app.core.dependencies import (
    get_order_service,
    get_product_service,
    get_scheduling_service,
)
from app.core.security import require_admin
from app.core.templates import templates
from app.modules.orders.cart import CartError, parse_cart_items
from app.modules.orders.domain import DeliveryMethod, OrderStatus
from app.modules.orders.schemas import (
    OrderCreateRequest,
    OrderUpdateRequest,
)
from app.modules.orders.service import OrderService
from app.modules.products.service import ProductService
from app.modules.scheduling.service import SchedulingService

router = APIRouter(
    prefix="/admin/orders",
    tags=["AdminOrders"],
    dependencies=[Depends(require_admin)],
)


def _error_toast(message: str) -> Response:
    headers = {
        "HX-Trigger": json.dumps({"show-toast": {"message": message, "type": "error"}})
    }
    return Response(status_code=204, headers=headers)


@router.get("", response_class=HTMLResponse)
def admin_dashboard(
    request: Request,
    status_filter: OrderStatus | None = Query(None, alias="status"),
    page: int = Query(1, ge=1),
    service: OrderService = Depends(get_order_service),
) -> HTMLResponse:
    page_size = 50
    orders = service.list_orders(
        status=status_filter, limit=page_size, offset=(page - 1) * page_size
    )

    if "hx-request" in request.headers:
        return templates.TemplateResponse(
            request=request,
            name="admin/partials/orders_table.html",
            context={"orders": orders},
        )

    return templates.TemplateResponse(
        request=request,
        name="admin/orders_dashboard.html",
        context={
            "orders": orders,
            "current_status": status_filter,
        },
    )


@router.get("/new", response_class=HTMLResponse)
def new_order_form(
    request: Request,
    product_service: ProductService = Depends(get_product_service),
    scheduling_service: SchedulingService = Depends(get_scheduling_service),
) -> HTMLResponse:
    products = product_service.list_products(only_active=True)
    available_dates = scheduling_service.get_available_dates()
    return templates.TemplateResponse(
        request=request,
        name="admin/order_create.html",
        context={
            "products": products,
            "available_dates": available_dates,
            "OrderStatuses": list(OrderStatus),
        },
    )


@router.post("")
def create_order(
    request: Request,
    customer_instagram: str = Form(...),
    cart_items_json: str = Form(...),
    delivery_date: datetime = Form(...),
    delivery_method: DeliveryMethod = Form(...),
    description: str = Form(...),
    order_status: OrderStatus = Form(OrderStatus.PENDING),
    amount_paid: int = Form(0),
    photos: list[UploadFile] | None = File(None),
    order_service: OrderService = Depends(get_order_service),
    product_service: ProductService = Depends(get_product_service),
    scheduling_service: SchedulingService = Depends(get_scheduling_service),
) -> Response:
    if photos is None:
        photos = []

    available_dates = [d.date for d in scheduling_service.get_available_dates()]
    if delivery_date.date() not in available_dates:
        return _error_toast("La fecha seleccionada no está disponible.")

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

    order_service.create_order(
        data=dto,
        photos=photos,
        status=order_status,
        amount_paid=amount_paid,
        created_by_admin=True,
    )

    return RedirectResponse(
        url=f"/admin/orders/{order.id}", status_code=status.HTTP_303_SEE_OTHER
    )


@router.get("/{order_id}", response_class=HTMLResponse)
def get_order_detail(
    request: Request,
    order_id: int,
    product_service: ProductService = Depends(get_product_service),
    service: OrderService = Depends(get_order_service),
) -> HTMLResponse:
    order = service.get_order(order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Pedido no encontrado")

    products = product_service.list_products(only_active=True)
    return templates.TemplateResponse(
        request=request,
        name="admin/order_detail.html",
        context={
            "order": order,
            "products": products,
            "OrderStatuses": [e.value for e in OrderStatus],
        },
    )


@router.post("/{order_id}/status")
def update_order_status(
    order_id: int,
    status: OrderStatus = Form(...),
    service: OrderService = Depends(get_order_service),
) -> RedirectResponse:
    service.change_status(order_id, status)

    return RedirectResponse(url=f"/admin/orders/{order_id}", status_code=303)


@router.post("/{order_id}/items")
def update_order_items(
    order_id: int,
    cart_items_json: str = Form(...),
    order_service: OrderService = Depends(get_order_service),
    product_service: ProductService = Depends(get_product_service),
) -> Response:
    current = order_service.get_order(order_id)
    if current is None:
        return _error_toast("La orden no existe.")

    stored_prices = {item.product_id: item.unit_price for item in current.items}

    try:
        parsed = parse_cart_items(
            cart_items_json, product_service, stored_prices=stored_prices
        )
    except CartError as exc:
        return _error_toast(exc.message)

    order = order_service.update_order_items(
        order_id, parsed.items, parsed.total_amount
    )
    if order is None:
        return _error_toast("La orden no existe.")

    return _redirect(f"/admin/orders/{order_id}")


@router.post("/{order_id}")
def update_order_details(
    order_id: int,
    delivery_date: str = Form(...),
    description: str = Form(...),
    delivery_method: DeliveryMethod = Form(...),
    amount_paid: int = Form(0),
    status: OrderStatus = Form(...),
    service: OrderService = Depends(get_order_service),
) -> RedirectResponse:
    dt = datetime.fromisoformat(delivery_date)

    order = service.get_order(order_id)
    if order:
        amount_paid = max(0, min(amount_paid, order.total_amount))
        if order.status != status:
            service.change_status(order_id, status)

    dto = OrderUpdateRequest(
        delivery_date=dt,
        description=description,
        delivery_method=delivery_method,
        amount_paid=amount_paid,
    )
    service.update_order(order_id, dto)

    return RedirectResponse(url="/admin/orders", status_code=303)


@router.post("/{order_id}/delete")
def delete_order(
    order_id: int,
    request: Request,
    service: OrderService = Depends(get_order_service),
) -> RedirectResponse:
    service.delete_order(order_id)
    return RedirectResponse(url="/admin/orders", status_code=status.HTTP_303_SEE_OTHER)
