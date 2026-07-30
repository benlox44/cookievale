from sqlalchemy import ARRAY, Boolean, Column, Integer, String, Text

from app.core.database import Base, TimestampMixin


class ProductModel(Base, TimestampMixin):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    price = Column(Integer, nullable=False)
    image_urls = Column(ARRAY(String), nullable=True)  # type: ignore[var-annotated]
    is_active = Column(Boolean, default=True, nullable=False)
    display_order = Column(Integer, default=0, nullable=False)
