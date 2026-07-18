from dataclasses import dataclass


@dataclass
class ProductDomainInfo:
    """
    Example of a pure domain entity for Product.
    For now we use Pydantic models (schemas.py) and SQLAlchemy (models.py),
    but this file maintains the architectural symmetry of Vertical Slicing.
    """

    id: int
    name: str
    price: float
    is_active: bool
