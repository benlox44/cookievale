from pydantic import BaseModel, ConfigDict, Field
from typing import Optional, List


class ProductBase(BaseModel):
    name: str
    description: Optional[str] = None
    price: float
    is_active: bool = True


class ProductCreate(ProductBase):
    pass


class ProductUpdate(ProductBase):
    pass


class ProductResponse(ProductBase):
    id: int
    image_urls: List[str] = Field(default_factory=list)
    model_config = ConfigDict(from_attributes=True)


class ProductReorderRequest(BaseModel):
    ordered_ids: List[int]
