from sqlalchemy import Column, Integer, Date
from app.core.database import Base


class AvailableDateModel(Base):
    __tablename__ = "available_dates"

    id = Column(Integer, primary_key=True, index=True)
    date = Column(Date, nullable=False, unique=True, index=True)
