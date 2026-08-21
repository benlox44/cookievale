from collections import defaultdict
from datetime import date, datetime

from app.core.config import TZ
from app.modules.orders.repository import OrderRepository
from app.modules.scheduling.domain import (
    AvailabilitySlot,
    AvailabilitySummary,
    AvailableDateOption,
)
from app.modules.scheduling.repository import AvailabilitySlotRepository


class SchedulingService:
    def __init__(
        self, repo: AvailabilitySlotRepository, order_repo: OrderRepository
    ) -> None:
        self.repo = repo
        self.order_repo = order_repo

    def _occupied_slot_ids(self) -> set[int]:
        return self.order_repo.get_occupied_slot_ids()

    def _purge_past_slots(self) -> None:
        today = datetime.now(tz=TZ).date()
        self.repo.delete_before(today)

    def get_summaries(self) -> list[AvailabilitySummary]:
        self._purge_past_slots()
        slots = self.repo.get_all()
        occupied = self._occupied_slot_ids()
        grouped: dict[date, list[AvailabilitySlot]] = defaultdict(list)
        for slot in slots:
            grouped[slot.date].append(slot)
        return [
            AvailabilitySummary(
                date=slot_date,
                free_slots=sum(slot.id not in occupied for slot in date_slots),
                total_slots=len(date_slots),
            )
            for slot_date, date_slots in grouped.items()
        ]

    def get_available_dates(self) -> list[AvailableDateOption]:
        return [
            AvailableDateOption(date=summary.date, free_slots=summary.free_slots)
            for summary in self.get_summaries()
            if summary.free_slots > 0
        ]

    def add_slot(self, new_date: date) -> AvailabilitySlot:
        today = datetime.now(tz=TZ).date()
        if new_date < today:
            raise ValueError("No se pueden registrar fechas pasadas.")
        return self.repo.create(new_date)

    def remove_one_free_slot(self, target_date: date) -> None:
        occupied = self._occupied_slot_ids()
        slot = next(
            (
                slot
                for slot in self.repo.get_all()
                if slot.date == target_date and slot.id not in occupied
            ),
            None,
        )
        if slot is None:
            raise ValueError(
                "No hay disponibilidades libres para eliminar en esa fecha."
            )
        self.repo.delete(slot.id)

    def get_slot_for_date(
        self, target_date: date, current_slot_id: int | None = None
    ) -> int:
        occupied = self._occupied_slot_ids()
        slots = [slot for slot in self.repo.get_all() if slot.date == target_date]
        if current_slot_id is not None and current_slot_id in {
            slot.id for slot in slots
        }:
            return current_slot_id
        for slot in slots:
            if slot.id not in occupied:
                return slot.id
        raise ValueError("La fecha seleccionada no tiene disponibilidades libres.")
