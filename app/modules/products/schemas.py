from pydantic import BaseModel, ConfigDict, Field
from typing import Optional, List


class ProductBase(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    description: Optional[str] = Field(default=None, max_length=2000)
    price: int = Field(gt=0)
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
    ordered_ids: List[int] = Field(min_length=1)
