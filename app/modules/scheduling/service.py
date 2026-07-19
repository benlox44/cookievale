from typing import List
from datetime import date
from app.modules.scheduling.repository import AvailableDateRepository
from app.modules.scheduling.domain import AvailableDate
from app.modules.orders.repository import OrderRepository


class SchedulingService:
    def __init__(self, repo: AvailableDateRepository, order_repo: OrderRepository):
        self.repo = repo
        self.order_repo = order_repo

    def _get_occupied_dates(self) -> set[date]:
        return self.order_repo.get_occupied_dates()

    def get_all_dates(self) -> List[AvailableDate]:
        all_dates = self.repo.get_all()
        occupied_dates = self._get_occupied_dates()
        for d in all_dates:
            if d.date in occupied_dates:
                d.is_occupied = True
        return all_dates

    def get_available_dates(self) -> List[AvailableDate]:
        all_dates = self.repo.get_all()
        occupied_dates = self._get_occupied_dates()
        return [d for d in all_dates if d.date not in occupied_dates]

    def add_date(self, new_date: date) -> AvailableDate:
        if self.repo.get_by_date(new_date):
            raise ValueError("La fecha ya está registrada.")
        return self.repo.create(new_date)

    def remove_date(self, date_id: int):
        target = self.repo.get_by_id(date_id)
        if not target:
            raise ValueError("Fecha no encontrada.")

        occupied_dates = self._get_occupied_dates()
        if target.date in occupied_dates:
            raise ValueError(
                f"Existe una orden activa en la fecha {target.date.strftime('%d/%m/%Y')}. Rechaza o elimina la orden primero para liberar la fecha."
            )

        self.repo.delete(date_id)
