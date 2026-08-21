from dataclasses import dataclass
from datetime import date


@dataclass
class AvailabilitySlot:
    id: int
    date: date


@dataclass
class AvailabilitySummary:
    date: date
    free_slots: int
    total_slots: int


@dataclass
class AvailableDateOption:
    date: date
    free_slots: int
