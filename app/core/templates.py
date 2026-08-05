from datetime import date, datetime
from enum import Enum

from fastapi.templating import Jinja2Templates

from app.core.config import BASE_URL

templates = Jinja2Templates(directory="templates")
templates.env.globals["base_url"] = BASE_URL

STATUS_LABELS = {
    "pending": "Pendiente",
    "confirmed": "Confirmada",
    "paid": "Pagada",
    "delivered": "Entregada",
    "rejected": "Rechazada",
}

DELIVERY_LABELS = {
    "pickup": "Retiro",
    "delivery": "Delivery",
}

# Hardcoded Spanish abbreviations so formatting never depends on the
# container's locale (strftime('%a') could otherwise render in English).
WEEKDAYS_SHORT = ["lun", "mar", "mié", "jue", "vie", "sáb", "dom"]
MONTHS_SHORT = [
    "ene",
    "feb",
    "mar",
    "abr",
    "may",
    "jun",
    "jul",
    "ago",
    "sep",
    "oct",
    "nov",
    "dic",
]


def clp(value: float) -> str:
    return f"${value:,.0f}"


def status_label(value: str | Enum) -> str:
    key = value.value if isinstance(value, Enum) else value
    return STATUS_LABELS.get(key, str(value))


def delivery_label(value: str | Enum) -> str:
    key = value.value if isinstance(value, Enum) else value
    return DELIVERY_LABELS.get(key, str(value))


def date_short(value: date | datetime) -> str:
    return f"{WEEKDAYS_SHORT[value.weekday()]}-{value.day:02d}-{MONTHS_SHORT[value.month - 1]}-{value.year}"


templates.env.filters["clp"] = clp
templates.env.filters["status_label"] = status_label
templates.env.filters["delivery_label"] = delivery_label
templates.env.filters["date_short"] = date_short
