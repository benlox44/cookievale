from dataclasses import dataclass
from typing import List, Optional


@dataclass
class Product:
    id: Optional[int]
    name: str
    price: int
    description: Optional[str] = None
    is_active: bool = True
    image_urls: Optional[List[str]] = None
    display_order: int = 0
