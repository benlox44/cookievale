from dataclasses import dataclass


@dataclass
class Product:
    id: int | None
    name: str
    price: int
    description: str | None = None
    is_active: bool = True
    image_urls: list[str] | None = None
    display_order: int = 0
