from pydantic import BaseModel, Field


class ProductBase(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=2000)
    price: int = Field(gt=0, lt=1_000_000_000)
    is_active: bool = True


class ProductInput(ProductBase):
    pass


class ProductReorderRequest(BaseModel):
    ordered_ids: list[int] = Field(min_length=1)
