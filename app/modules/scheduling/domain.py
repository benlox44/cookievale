from dataclasses import dataclass
from datetime import date


@dataclass
class AvailabilitySlot:
    id: int
    date: date


@dataclass
class AvailableSlotOption:
    date: date
    free_slots: int
