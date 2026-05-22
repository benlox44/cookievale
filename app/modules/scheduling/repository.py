from typing import List, Optional
from datetime import date
from sqlalchemy.orm import Session
from sqlalchemy import select, exc
from app.modules.scheduling.models import AvailableDateModel
from app.modules.scheduling.domain import AvailableDate

class AvailableDateRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_all(self, limit: int = 100, offset: int = 0) -> List[AvailableDate]:
        results = self.db.execute(select(AvailableDateModel).order_by(AvailableDateModel.date.asc()).limit(limit).offset(offset))
        models = results.scalars().all()
        return [AvailableDate(id=m.id, date=m.date) for m in models]
    
    def get_by_date(self, target_date: date) -> Optional[AvailableDate]:
        result = self.db.execute(select(AvailableDateModel).where(AvailableDateModel.date == target_date))
        m = result.scalars().first()
        if m:
            return AvailableDate(id=m.id, date=m.date)
        return None
    
    def get_by_id(self, id: int) -> Optional[AvailableDate]:
        result = self.db.execute(select(AvailableDateModel).where(AvailableDateModel.id == id))
        m = result.scalars().first()
        if m:
            return AvailableDate(id=m.id, date=m.date)
        return None

    def create(self, target_date: date) -> AvailableDate:
        model = AvailableDateModel(date=target_date)
        self.db.add(model)
        try:
            self.db.commit()
            self.db.refresh(model)
        except exc.IntegrityError:
            self.db.rollback()
            raise ValueError("La fecha ya existe.")
        return AvailableDate(id=model.id, date=model.date)

    def delete(self, id: int) -> None:
        model = self.db.get(AvailableDateModel, id)
        if model:
            self.db.delete(model)
            self.db.commit()
