
from pydantic import BaseModel, ConfigDict, Field


class ProductBase(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=2000)
    price: int = Field(gt=0)
    is_active: bool = True


class ProductCreate(ProductBase):
    pass


class ProductUpdate(ProductBase):
    pass


class ProductResponse(ProductBase):
    id: int
    image_urls: list[str] = Field(default_factory=list)
    model_config = ConfigDict(from_attributes=True)


class ProductReorderRequest(BaseModel):
    ordered_ids: list[int] = Field(min_length=1)
