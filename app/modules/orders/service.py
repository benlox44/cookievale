import os
import shutil
import uuid
from typing import List, Optional
from fastapi import UploadFile

from app.modules.orders.domain import Order, OrderStatus, OrderItem
from app.modules.orders.repository import OrderRepository
from app.modules.orders.schemas import OrderCreateRequest, OrderUpdateRequest


class OrderService:
    def __init__(self, repository: OrderRepository) -> None:
        self.repository = repository

    def create_order(self, data: OrderCreateRequest, photos: List[UploadFile]) -> Order:
        items = [
            OrderItem(
                product_id=i.product_id, quantity=i.quantity, unit_price=i.unit_price
            )
            for i in data.items
        ]

        order = Order(
            customer_instagram=data.customer_instagram,
            delivery_date=data.delivery_date,
            description=data.description,
            total_amount=data.total_amount,
            amount_paid=0.0,
            items=items,
        )

        # We must save first to generate a unique DB ID for creating the isolated photo folder
        order = self.repository.save(order)

        saved_paths = []
        if photos and photos[0].filename:
            order_dir = os.path.join(
                os.environ["CONTAINER_MEDIA_PATH"], f"orders/{order.id}"
            )
            os.makedirs(order_dir, exist_ok=True)

            for photo in photos[:3]:
                if not photo.filename:
                    continue
                ext = photo.filename.split(".")[-1]
                filename = f"{uuid.uuid4().hex}.{ext}"
                filepath = os.path.join(order_dir, filename)

                with open(filepath, "wb") as buffer:
                    shutil.copyfileobj(photo.file, buffer)

                saved_paths.append(f"/media/orders/{order.id}/{filename}")

        if saved_paths:
            order.reference_photos = saved_paths
            order = self.repository.save(order)

        return order

    def get_order(self, order_id: int) -> Optional[Order]:
        return self.repository.get_by_id(order_id)

    def update_order(self, order_id: int, data: OrderUpdateRequest) -> Optional[Order]:
        order = self.repository.get_by_id(order_id)
        if not order:
            return None

        order.delivery_date = data.delivery_date
        order.description = data.description
        order.amount_paid = data.amount_paid
        return self.repository.save(order)

    def change_status(self, order_id: int, new_status: OrderStatus) -> Optional[Order]:
        order = self.repository.get_by_id(order_id)
        if not order:
            return None

        order.status = new_status
        return self.repository.save(order)

    def delete_order(self, order_id: int) -> None:
        self.repository.delete(order_id)
