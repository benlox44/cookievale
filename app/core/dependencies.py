from fastapi import Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.modules.orders.repository import SQLAlchemyOrderRepository
from app.modules.orders.service import OrderService
from app.modules.products.repository import ProductRepository
from app.modules.products.service import ProductService
from app.modules.scheduling.repository import AvailableDateRepository
from app.modules.scheduling.service import SchedulingService


def get_order_service(db: Session = Depends(get_db)) -> OrderService:
    repo = SQLAlchemyOrderRepository(db)
    return OrderService(repo)


def get_product_service(db: Session = Depends(get_db)) -> ProductService:
    repo = ProductRepository(db)
    return ProductService(repo)


def get_scheduling_service(db: Session = Depends(get_db)) -> SchedulingService:
    return SchedulingService(AvailableDateRepository(db), SQLAlchemyOrderRepository(db))
