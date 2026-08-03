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


def clp(value: float) -> str:
    return f"${value:,.0f}"


def status_label(value: str | Enum) -> str:
    key = value.value if isinstance(value, Enum) else value
    return STATUS_LABELS.get(key, str(value))


def delivery_label(value: str | Enum) -> str:
    key = value.value if isinstance(value, Enum) else value
    return DELIVERY_LABELS.get(key, str(value))


templates.env.filters["clp"] = clp
templates.env.filters["status_label"] = status_label
templates.env.filters["delivery_label"] = delivery_label
