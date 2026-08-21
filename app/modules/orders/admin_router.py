from datetime import datetime
from urllib.parse import quote

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
)
from fastapi.responses import HTMLResponse, RedirectResponse

from app.core.dependencies import (
    get_order_service,
    get_product_service,
    get_scheduling_service,
)
from app.core.htmx import error_toast, redirect
from app.core.security import require_admin
from app.core.templates import templates
from app.modules.orders.cart import CartError, parse_cart_items
from app.modules.orders.domain import DeliveryMethod, OrderStatus
from app.modules.orders.schemas import OrderUpdateRequest
from app.modules.orders.service import OrderService
from app.modules.products.service import ProductService
from app.modules.scheduling.domain import AvailableDateOption
from app.modules.scheduling.service import SchedulingService

router = APIRouter(
    prefix="/admin/orders",
    tags=["AdminOrders"],
    dependencies=[Depends(require_admin)],
)


@router.get("", response_class=HTMLResponse)
def admin_dashboard(
    request: Request,
    include_closed: bool = Query(False),
    page: int = Query(1, ge=1),
    sort_by: str | None = Query(None),
    sort_dir: str = Query("desc"),
    service: OrderService = Depends(get_order_service),
) -> HTMLResponse:
    if sort_by is None:
        sort_by = "date"
    if sort_by not in ("id", "date"):
        sort_by = "date"
    if sort_dir not in ("asc", "desc"):
        sort_dir = "desc"

    page_size = 50
    orders = service.list_orders(
        include_closed=include_closed,
        limit=page_size,
        offset=(page - 1) * page_size,
        sort_by=sort_by,
        sort_dir=sort_dir,
    )
    total = service.count_orders(include_closed=include_closed)
    total_pages = max(1, (total + page_size - 1) // page_size)

    context = {
        "orders": orders,
        "include_closed": include_closed,
        "current_sort_by": sort_by,
        "current_sort_dir": sort_dir,
        "page": page,
        "total_pages": total_pages,
    }

    if "hx-request" in request.headers:
        return templates.TemplateResponse(
            request=request,
            name="admin/partials/orders_table.html",
            context=context,
        )

    return templates.TemplateResponse(
        request=request,
        name="admin/orders_dashboard.html",
        context=context,
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
            "weekdays": [
                "Lunes",
                "Martes",
                "Miércoles",
                "Jueves",
                "Viernes",
                "Sábado",
                "Domingo",
            ],
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

    try:
        availability_slot_id = scheduling_service.get_slot_for_date(
            delivery_date.date()
        )
    except ValueError:
        return error_toast("La fecha seleccionada no está disponible.")

    try:
        parsed = parse_cart_items(cart_items_json, product_service)
    except CartError as exc:
        return error_toast(exc.message)

    try:
        order_service.create_from_parsed_cart(
            cart=parsed,
            customer_instagram=customer_instagram,
            delivery_date=delivery_date,
            availability_slot_id=availability_slot_id,
            delivery_method=delivery_method,
            description=description,
            photos=photos,
            status=order_status,
            amount_paid=amount_paid,
            created_by_admin=True,
        )
    except ValueError as exc:
        return error_toast(str(exc))

    return redirect("/admin/orders")


@router.get("/{order_id}", response_class=HTMLResponse)
def get_order_detail(
    request: Request,
    order_id: int,
    product_service: ProductService = Depends(get_product_service),
    scheduling_service: SchedulingService = Depends(get_scheduling_service),
    service: OrderService = Depends(get_order_service),
) -> HTMLResponse:
    order = service.get_order(order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Pedido no encontrado")

    products = product_service.list_products(only_active=True)
    available_dates = scheduling_service.get_available_dates()
    order_date = order.delivery_date.date()
    if not any(option.date == order_date for option in available_dates):
        available_dates = [
            AvailableDateOption(date=order_date, free_slots=0),
            *available_dates,
        ]
    return templates.TemplateResponse(
        request=request,
        name="admin/order_detail.html",
        context={
            "order": order,
            "products": products,
            "available_dates": available_dates,
            "weekdays": [
                "Lunes",
                "Martes",
                "Miércoles",
                "Jueves",
                "Viernes",
                "Sábado",
                "Domingo",
            ],
            "OrderStatuses": [e.value for e in OrderStatus],
        },
    )


@router.post("/{order_id}/status")
def update_order_status(
    order_id: int,
    status: OrderStatus = Form(...),
    service: OrderService = Depends(get_order_service),
) -> RedirectResponse:
    # Un-rejecting an order back onto an already-occupied date is rejected by
    # the database; surface it instead of silently failing.
    try:
        service.change_status(order_id, status)
    except ValueError as exc:
        return RedirectResponse(
            url=f"/admin/orders/{order_id}?error={quote(str(exc))}", status_code=303
        )

    return RedirectResponse(url=f"/admin/orders/{order_id}", status_code=303)


@router.post("/{order_id}")
def update_order_details(
    order_id: int,
    delivery_date: str = Form(...),
    description: str = Form(...),
    delivery_method: DeliveryMethod = Form(...),
    amount_paid: int = Form(0),
    status: OrderStatus = Form(...),
    cart_items_json: str | None = Form(None),
    existing_photos: list[str] = Form([]),
    image_order: str = Form("[]"),
    photos: list[UploadFile] | None = File(None),
    service: OrderService = Depends(get_order_service),
    product_service: ProductService = Depends(get_product_service),
    scheduling_service: SchedulingService = Depends(get_scheduling_service),
) -> RedirectResponse:
    try:
        dt = datetime.fromisoformat(delivery_date)
    except ValueError:
        return RedirectResponse(
            url=f"/admin/orders/{order_id}?error={quote('La fecha de entrega no es válida.')}",
            status_code=303,
        )

    order = service.get_order(order_id)
    if not order:
        return RedirectResponse(url="/admin/orders", status_code=303)

    try:
        availability_slot_id = scheduling_service.get_slot_for_date(
            dt.date(), current_slot_id=order.availability_slot_id
        )
    except ValueError:
        return RedirectResponse(
            url=f"/admin/orders/{order_id}?error={quote('La fecha seleccionada no está disponible.')}",
            status_code=303,
        )

    if cart_items_json:
        stored_prices = {item.product_id: item.unit_price for item in order.items}
        try:
            parsed = parse_cart_items(
                cart_items_json, product_service, stored_prices=stored_prices
            )
        except CartError as exc:
            return RedirectResponse(
                url=f"/admin/orders/{order_id}?error={quote(exc.message)}",
                status_code=303,
            )
        order = service.update_order_items(order_id, parsed.items, parsed.total_amount)
        if order is None:
            return RedirectResponse(url="/admin/orders", status_code=303)

    if order.status != status:
        service.change_status(order_id, status)
    # change_status auto-pays when moving to paid/delivered, so the
    # manual amount only applies to the other statuses (still capped).
    if status in (OrderStatus.PAID, OrderStatus.DELIVERED):
        amount_paid = order.total_amount
    else:
        amount_paid = max(0, min(amount_paid, order.total_amount))

    dto = OrderUpdateRequest(
        delivery_date=dt,
        availability_slot_id=availability_slot_id,
        description=description,
        delivery_method=delivery_method,
        amount_paid=amount_paid,
    )
    try:
        service.update_order(order_id, dto, existing_photos, image_order, photos)
    except ValueError as exc:
        return RedirectResponse(
            url=f"/admin/orders/{order_id}?error={quote(str(exc))}", status_code=303
        )

    return RedirectResponse(url="/admin/orders", status_code=303)


@router.post("/{order_id}/delete")
def delete_order(
    order_id: int,
    request: Request,
    service: OrderService = Depends(get_order_service),
) -> RedirectResponse:
    service.delete_order(order_id)
    return RedirectResponse(url="/admin/orders", status_code=303)
