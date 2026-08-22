from datetime import date, datetime, timedelta

import pytest

from app.core.config import TZ
from app.modules.scheduling.domain import AvailabilitySlot
from app.modules.scheduling.service import SchedulingService


class FakeSlotRepository:
    def __init__(self, slots: list[AvailabilitySlot] | None = None) -> None:
        self._slots = {s.id: s for s in (slots or [])}
        self._next_id = max(self._slots.keys(), default=0) + 1

    def get_all(self) -> list[AvailabilitySlot]:
        return sorted(self._slots.values(), key=lambda s: s.date)

    def get_by_id(self, slot_id: int) -> AvailabilitySlot | None:
        return self._slots.get(slot_id)

    def create(self, target_date: date) -> AvailabilitySlot:
        slot = AvailabilitySlot(id=self._next_id, date=target_date)
        self._next_id += 1
        self._slots[slot.id] = slot
        return slot

    def delete(self, slot_id: int) -> None:
        self._slots.pop(slot_id, None)

    def delete_before(self, target: date) -> int:
        stale = [s for s in self._slots.values() if s.date < target]
        for s in stale:
            self._slots.pop(s.id, None)
        return len(stale)


class FakeOrderRepository:
    def __init__(self, occupied: set[int] | None = None) -> None:
        self._occupied = occupied or set()

    def get_occupied_slot_ids(self) -> set[int]:
        return self._occupied


def make_service(
    slots: list[AvailabilitySlot] | None = None,
    occupied: set[int] | None = None,
) -> tuple[SchedulingService, FakeSlotRepository]:
    slot_repo = FakeSlotRepository(slots)
    order_repo = FakeOrderRepository(occupied)
    return SchedulingService(slot_repo, order_repo), slot_repo


def _today() -> date:
    return datetime.now(tz=TZ).date()


@pytest.fixture
def slots() -> list[AvailabilitySlot]:
    today = _today()
    return [
        AvailabilitySlot(id=1, date=today + timedelta(days=1)),
        AvailabilitySlot(id=2, date=today + timedelta(days=1)),
        AvailabilitySlot(id=3, date=today + timedelta(days=3)),
    ]


def test_get_slot_for_date_returns_free_slot(slots: list[AvailabilitySlot]) -> None:
    service, _ = make_service(slots, occupied={1})
    assert service.get_slot_for_date(slots[0].date) == 2


def test_get_slot_for_date_keeps_current_slot(slots: list[AvailabilitySlot]) -> None:
    service, _ = make_service(slots, occupied={2, 3})
    assert service.get_slot_for_date(slots[0].date, current_slot_id=1) == 1


def test_get_slot_for_date_raises_when_none_free(slots: list[AvailabilitySlot]) -> None:
    service, _ = make_service(slots, occupied={1, 2, 3})
    with pytest.raises(ValueError):
        service.get_slot_for_date(slots[0].date)


def test_add_slot_rejects_past_dates() -> None:
    service, _ = make_service()
    with pytest.raises(ValueError):
        service.add_slot(_today() - timedelta(days=1))


def test_add_slot_creates_future_date() -> None:
    service, _ = make_service()
    created = service.add_slot(_today() + timedelta(days=5))
    assert created.date == _today() + timedelta(days=5)


def test_remove_one_free_slot_removes_free_slot(slots: list[AvailabilitySlot]) -> None:
    service, slot_repo = make_service(slots, occupied={1})
    service.remove_one_free_slot(slots[0].date)
    assert 2 not in {s.id for s in slot_repo.get_all()}


def test_remove_one_free_slot_raises_when_none(slots: list[AvailabilitySlot]) -> None:
    service, _ = make_service(slots, occupied={1, 2})
    with pytest.raises(ValueError):
        service.remove_one_free_slot(slots[0].date)


def test_get_available_dates_counts_free_slots(
    slots: list[AvailabilitySlot],
) -> None:
    service, _ = make_service(slots, occupied={1})
    dates = service.get_available_dates()
    by_date = {o.date: o.free_slots for o in dates}
    assert by_date[slots[0].date] == 1
    assert by_date[slots[2].date] == 1


def test_get_free_slots_purges_past_dates(slots: list[AvailabilitySlot]) -> None:
    stale = AvailabilitySlot(id=99, date=_today() - timedelta(days=1))
    service, _ = make_service([*slots, stale])
    free = service.get_free_slots()
    assert 99 not in {s.id for s in free}
