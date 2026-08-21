from datetime import date
from typing import Protocol

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.modules.scheduling.domain import AvailabilitySlot
from app.modules.scheduling.models import AvailabilitySlotModel


class AvailabilitySlotRepository(Protocol):
    def get_all(self) -> list[AvailabilitySlot]: ...
    def get_by_id(self, slot_id: int) -> AvailabilitySlot | None: ...
    def create(self, target_date: date) -> AvailabilitySlot: ...
    def delete(self, slot_id: int) -> None: ...
    def delete_before(self, target: date) -> int: ...


class SQLAlchemyAvailabilitySlotRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_all(self) -> list[AvailabilitySlot]:
        stmt = select(AvailabilitySlotModel).order_by(AvailabilitySlotModel.date.asc())
        return [self._to_domain(model) for model in self.db.scalars(stmt).all()]

    def get_by_id(self, slot_id: int) -> AvailabilitySlot | None:
        model = self.db.get(AvailabilitySlotModel, slot_id)
        return self._to_domain(model) if model else None

    def create(self, target_date: date) -> AvailabilitySlot:
        model = AvailabilitySlotModel(date=target_date)
        self.db.add(model)
        self.db.commit()
        self.db.refresh(model)
        return self._to_domain(model)

    def delete(self, slot_id: int) -> None:
        model = self.db.get(AvailabilitySlotModel, slot_id)
        if model:
            self.db.delete(model)
            self.db.commit()

    def delete_before(self, target: date) -> int:
        result = self.db.execute(
            delete(AvailabilitySlotModel).where(AvailabilitySlotModel.date < target)
        )
        self.db.commit()
        return int(result.rowcount or 0)  # type: ignore[attr-defined]

    @staticmethod
    def _to_domain(model: AvailabilitySlotModel) -> AvailabilitySlot:
        return AvailabilitySlot(id=model.id, date=model.date)
