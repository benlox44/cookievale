import calendar
from datetime import date, datetime

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import HTMLResponse

from app.core.config import TZ
from app.core.dependencies import get_order_service
from app.core.security import require_admin
from app.core.templates import templates
from app.modules.orders.service import OrderService

router = APIRouter(
    prefix="/admin/stats",
    tags=["AdminStats"],
    dependencies=[Depends(require_admin)],
)

PRESET_OPTIONS = [
    {"value": "all", "label": "Histórico"},
    {"value": "month", "label": "Este mes"},
    {"value": "last_month", "label": "Mes pasado"},
    {"value": "year", "label": "Este año"},
    {"value": "custom", "label": "Personalizado"},
]
VALID_PRESETS = frozenset(opt["value"] for opt in PRESET_OPTIONS)


def _parse_iso_date(raw: str | None) -> date | None:
    if not raw:
        return None
    try:
        return date.fromisoformat(raw.strip())
    except ValueError:
        return None


def _preset_ranges(
    today: date, bounds: tuple[date | None, date | None]
) -> dict[str, tuple[date | None, date | None]]:
    month_last = calendar.monthrange(today.year, today.month)[1]
    prev_year, prev_month = (
        (today.year - 1, 12) if today.month == 1 else (today.year, today.month - 1)
    )
    prev_last = calendar.monthrange(prev_year, prev_month)[1]

    return {
        "all": bounds,
        "month": (
            date(today.year, today.month, 1),
            date(today.year, today.month, month_last),
        ),
        "last_month": (
            date(prev_year, prev_month, 1),
            date(prev_year, prev_month, prev_last),
        ),
        "year": (date(today.year, 1, 1), date(today.year, 12, 31)),
    }


def _resolve_date_range(
    preset: str | None,
    raw_from: str | None,
    raw_to: str | None,
    today: date,
    bounds: tuple[date | None, date | None],
) -> tuple[str, date | None, date | None]:
    ranges = _preset_ranges(today, bounds)
    parsed_from = _parse_iso_date(raw_from)
    parsed_to = _parse_iso_date(raw_to)

    if preset not in VALID_PRESETS:
        if parsed_from is not None or parsed_to is not None:
            preset = "custom"
        else:
            preset = "all"

    if preset in ranges:
        start, end = ranges[preset]
        return preset, start, end

    if parsed_from is not None and parsed_to is not None and parsed_from > parsed_to:
        parsed_from, parsed_to = parsed_to, parsed_from

    # Match manual dates back to a known preset when they coincide exactly
    for name, (start, end) in ranges.items():
        if parsed_from == start and parsed_to == end:
            return name, start, end

    return "custom", parsed_from, parsed_to


@router.get("", response_class=HTMLResponse)
def stats_dashboard(
    request: Request,
    preset: str | None = Query(None),
    date_from: str | None = Query(None),
    date_to: str | None = Query(None),
    service: OrderService = Depends(get_order_service),
) -> HTMLResponse:
    today = datetime.now(tz=TZ).date()
    bounds = service.get_order_date_bounds()
    active_preset, resolved_from, resolved_to = _resolve_date_range(
        preset, date_from, date_to, today, bounds
    )
    query_from = None if active_preset == "all" else resolved_from
    query_to = None if active_preset == "all" else resolved_to
    stats = service.get_sales_stats(date_from=query_from, date_to=query_to)

    context = {
        "stats": stats,
        "preset_options": PRESET_OPTIONS,
        "active_preset": active_preset,
        "date_from": resolved_from.isoformat() if resolved_from else "",
        "date_to": resolved_to.isoformat() if resolved_to else "",
    }

    if "hx-request" in request.headers:
        return templates.TemplateResponse(
            request=request,
            name="components/admin/stats_content.html",
            context=context,
        )

    return templates.TemplateResponse(
        request=request,
        name="admin/stats_dashboard.html",
        context=context,
    )
