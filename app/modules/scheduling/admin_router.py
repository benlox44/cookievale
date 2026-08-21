from datetime import date, datetime

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse

from app.core.config import TZ
from app.core.dependencies import get_scheduling_service
from app.core.security import require_admin
from app.core.templates import templates
from app.modules.scheduling.service import SchedulingService

router = APIRouter(
    prefix="/admin/dates",
    tags=["admin-dates"],
    dependencies=[Depends(require_admin)],
)


@router.get("", response_class=HTMLResponse)
def dates_dashboard(
    request: Request, service: SchedulingService = Depends(get_scheduling_service)
) -> HTMLResponse:
    dates = service.get_summaries()
    today = datetime.now(tz=TZ).date().strftime("%Y-%m-%d")
    return templates.TemplateResponse(
        request=request,
        name="admin/dates_dashboard.html",
        context={
            "dates": dates,
            "today": today,
            "weekdays": [
                "Lunes",
                "Martes",
                "Miércoles",
                "Jueves",
                "Viernes",
                "Sábado",
                "Domingo",
            ],
        },
    )


@router.post("", response_model=None)
def add_date(
    selected_date: date = Form(...),
    service: SchedulingService = Depends(get_scheduling_service),
) -> RedirectResponse | JSONResponse:
    try:
        service.add_slot(selected_date)
    except ValueError as e:
        return JSONResponse({"detail": str(e)}, status_code=409)
    return RedirectResponse("/admin/dates", status_code=303)


@router.delete("/{target_date}", response_model=None)
def delete_date(
    target_date: date,
    service: SchedulingService = Depends(get_scheduling_service),
) -> dict[str, str] | JSONResponse:
    try:
        service.remove_one_free_slot(target_date)
    except ValueError as e:
        return JSONResponse({"detail": str(e)}, status_code=409)
    return {"status": "ok"}
