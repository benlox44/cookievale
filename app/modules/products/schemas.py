from pydantic import BaseModel, Field


class ProductInput(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=2000)
    price: int = Field(gt=0, lt=1_000_000_000)
    is_active: bool = True


class ProductReorderRequest(BaseModel):
    ordered_ids: list[int] = Field(min_length=1)
