from dataclasses import dataclass
from datetime import date

@dataclass
class AvailableDate:
    id: int
    date: date
    is_occupied: bool = False
