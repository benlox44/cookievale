from datetime import date
from typing import Protocol

from sqlalchemy import exc, select
from sqlalchemy.orm import Session

from app.modules.scheduling.domain import AvailableDate
from app.modules.scheduling.models import AvailableDateModel


class AvailableDateRepositoryProtocol(Protocol):
    def get_all(self, limit: int = 100, offset: int = 0) -> list[AvailableDate]: ...
    def get_by_date(self, target_date: date) -> AvailableDate | None: ...
    def get_by_id(self, id: int) -> AvailableDate | None: ...
    def create(self, target_date: date) -> AvailableDate: ...
    def delete(self, id: int) -> None: ...


class AvailableDateRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_all(self, limit: int = 100, offset: int = 0) -> list[AvailableDate]:
        results = self.db.execute(
            select(AvailableDateModel)
            .order_by(AvailableDateModel.date.asc())
            .limit(limit)
            .offset(offset)
        )
        models = results.scalars().all()
        return [self._to_domain(m) for m in models]

    def get_by_date(self, target_date: date) -> AvailableDate | None:
        result = self.db.execute(
            select(AvailableDateModel).where(AvailableDateModel.date == target_date)
        )
        m = result.scalars().first()
        if m:
            return self._to_domain(m)
        return None

    def get_by_id(self, id: int) -> AvailableDate | None:
        result = self.db.execute(
            select(AvailableDateModel).where(AvailableDateModel.id == id)
        )
        m = result.scalars().first()
        if m:
            return self._to_domain(m)
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
        return self._to_domain(model)

    def _to_domain(self, model: AvailableDateModel) -> AvailableDate:
        mid: int = model.id  # type: ignore[assignment]
        mdate: date = model.date  # type: ignore[assignment]
        return AvailableDate(id=mid, date=mdate)

    def delete(self, id: int) -> None:
        model = self.db.get(AvailableDateModel, id)
        if model:
            self.db.delete(model)
            self.db.commit()
