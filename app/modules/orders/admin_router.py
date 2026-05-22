from fastapi import APIRouter, Depends, Request, Query, Form, HTTPException, status
from fastapi.responses import HTMLResponse, RedirectResponse
from typing import Optional

from app.core.templates import templates
from app.core.dependencies import get_order_service
from app.core.security import get_current_admin
from app.modules.orders.service import OrderService
from app.modules.orders.schemas import OrderUpdateRequest
from app.modules.orders.domain import OrderStatus

router = APIRouter(prefix="/admin/orders", tags=["AdminOrders"])


@router.get("", response_class=HTMLResponse)
def admin_dashboard(
    request: Request,
    status_filter: Optional[OrderStatus] = Query(None, alias="status"),
    service: OrderService = Depends(get_order_service),
    admin: str = Depends(get_current_admin),
):
    orders = service.repository.list_all(status=status_filter)


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
            "admin_user": admin,
            "current_status": status_filter,
        },
    )


@router.get("/{order_id}", response_class=HTMLResponse)
def get_order_detail(
    request: Request,
    order_id: int,
    service: OrderService = Depends(get_order_service),
    admin: str = Depends(get_current_admin),
):
    order = service.get_order(order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Pedido no encontrado")

    return templates.TemplateResponse(
        request=request,
        name="admin/order_detail.html",
        context={
            "order": order,
            "admin_user": admin,
            "OrderStatuses": [e.value for e in OrderStatus],
        },
    )


@router.post("/{order_id}/status")
def update_order_status(
    order_id: int,
    status: OrderStatus = Form(...),
    service: OrderService = Depends(get_order_service),
    admin: str = Depends(get_current_admin),
):
    service.change_status(order_id, status)

    return RedirectResponse(url=f"/admin/orders/{order_id}", status_code=303)


@router.post("/{order_id}")
def update_order_details(
    order_id: int,
    delivery_date: str = Form(...),
    description: str = Form(...),
    amount_paid: float = Form(0.0),
    status: OrderStatus = Form(...),
    service: OrderService = Depends(get_order_service),
    admin: str = Depends(get_current_admin),
):
    from datetime import datetime

    dt = datetime.fromisoformat(delivery_date)

    order = service.get_order(order_id)
    if order:
        amount_paid = max(0.0, min(amount_paid, order.total_amount))
        if order.status != status:
            service.change_status(order_id, status)

    dto = OrderUpdateRequest(
        delivery_date=dt, description=description, amount_paid=amount_paid
    )
    service.update_order(order_id, dto)

    return RedirectResponse(url="/admin/orders", status_code=303)


@router.post("/{order_id}/delete")
def delete_order(
    order_id: int,
    request: Request,
    service: OrderService = Depends(get_order_service),
    admin: str = Depends(get_current_admin),
):
    service.delete_order(order_id)
    return RedirectResponse(url="/admin/orders", status_code=status.HTTP_303_SEE_OTHER)
