from sqlalchemy.orm import Session
from fastapi import Depends

from app.core.database import get_db
from app.modules.orders.repository import SQLAlchemyOrderRepository
from app.modules.orders.service import OrderService


def get_order_service(db: Session = Depends(get_db)) -> OrderService:
    repo = SQLAlchemyOrderRepository(db)
    return OrderService(repo)
