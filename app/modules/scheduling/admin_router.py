from fastapi import APIRouter, Depends, Request, Form
from fastapi.responses import HTMLResponse, JSONResponse
from app.core.security import get_current_admin
from app.core.templates import templates
from app.core.dependencies import get_scheduling_service
from app.modules.scheduling.service import SchedulingService
from datetime import date

router = APIRouter(
    prefix="/admin/dates",
    tags=["admin-dates"],
    dependencies=[Depends(get_current_admin)],
)


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


@router.post("")
def add_date(
    selected_date: date = Form(...),
    service: SchedulingService = Depends(get_scheduling_service),
):
    try:
        new_date = service.add_date(selected_date)
    except ValueError as e:
        return JSONResponse({"detail": str(e)}, status_code=409)
    return {"status": "ok", "id": new_date.id}


@router.delete("/{date_id}")
def delete_date(
    date_id: int,
    service: SchedulingService = Depends(get_scheduling_service),
):
    try:
        service.remove_date(date_id)
    except ValueError as e:
        return JSONResponse({"detail": str(e)}, status_code=409)
    return {"status": "ok"}
