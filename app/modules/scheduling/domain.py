from dataclasses import dataclass
from datetime import date


@dataclass
class AvailabilitySlot:
    id: int
    date: date


@dataclass
class AvailableDateOption:
    date: date
    free_slots: int
