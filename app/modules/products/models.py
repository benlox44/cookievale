from sqlalchemy import Column, Integer, String, Boolean, Float, Text, ARRAY
from app.core.database import Base


class ProductModel(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    price = Column(Float, nullable=False)
    image_urls = Column(ARRAY(String), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    display_order = Column(Integer, default=0, nullable=False)
