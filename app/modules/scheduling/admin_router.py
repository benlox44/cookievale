from fastapi import APIRouter, Depends, Request, Form
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import get_current_admin
from app.core.templates import templates
from app.modules.scheduling.service import SchedulingService
from app.modules.scheduling.repository import AvailableDateRepository
from app.modules.orders.repository import SQLAlchemyOrderRepository
from datetime import date

router = APIRouter(
    prefix="/admin/dates",
    tags=["admin-dates"],
    dependencies=[Depends(get_current_admin)],
)


def get_scheduling_service(db: Session = Depends(get_db)) -> SchedulingService:
    return SchedulingService(AvailableDateRepository(db), SQLAlchemyOrderRepository(db))


@router.get("", response_class=HTMLResponse)
def dates_dashboard(
    request: Request, service: SchedulingService = Depends(get_scheduling_service)
):
    dates = service.get_all_dates()
    today = date.today().strftime("%Y-%m-%d")
    return templates.TemplateResponse(
        request=request,
        name="admin/dates_dashboard.html",
        context={"dates": dates, "today": today},
    )


@router.get("/list", response_class=HTMLResponse)
def get_dates_list(
    request: Request, service: SchedulingService = Depends(get_scheduling_service)
):
    dates = service.get_all_dates()
    return templates.TemplateResponse(
        request=request, name="admin/partials/dates_list.html", context={"dates": dates}
    )


@router.post("", response_class=HTMLResponse)
def add_date(
    request: Request,
    selected_date: date = Form(...),
    service: SchedulingService = Depends(get_scheduling_service),
):
    try:
        service.add_date(selected_date)
        resp = templates.TemplateResponse(
            request=request,
            name="admin/partials/dates_list.html",
            context={"dates": service.get_all_dates()},
        )
        resp.headers["HX-Trigger"] = '{"show-toast": {"message": "Fecha agregada"}}'
        return resp
    except ValueError:
        return templates.TemplateResponse(
            request=request,
            name="admin/partials/dates_list.html",
            context={"dates": service.get_all_dates()},
        )


@router.delete("/{date_id}", response_class=HTMLResponse)
def delete_date(
    request: Request,
    date_id: int,
    service: SchedulingService = Depends(get_scheduling_service),
):
    try:
        service.remove_date(date_id)
        resp = templates.TemplateResponse(
            request=request,
            name="admin/partials/dates_list.html",
            context={"dates": service.get_all_dates()},
        )
        resp.headers["HX-Trigger"] = '{"show-toast": {"message": "Fecha eliminada"}}'
        return resp
    except ValueError:
        return templates.TemplateResponse(
            request=request,
            name="admin/partials/dates_list.html",
            context={"dates": service.get_all_dates()},
        )
