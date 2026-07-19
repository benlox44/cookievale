import os
import shutil
import logging
from typing import List, Optional
from fastapi import UploadFile

from app.core.telegram import TelegramNotifier
from app.core.uploads import save_uploads
from app.modules.orders.domain import Order, OrderStatus, OrderItem
from app.modules.orders.repository import OrderRepository
from app.modules.orders.schemas import OrderCreateRequest, OrderUpdateRequest

logger = logging.getLogger(__name__)


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
            delivery_method=data.delivery_method,
            total_amount=data.total_amount,
            amount_paid=0,
            items=items,
        )

        order = self.repository.save(order)

        if photos and photos[0].filename:
            order_dir = os.path.join(
                os.environ["CONTAINER_MEDIA_PATH"], f"orders/{order.id}"
            )
            url_prefix = f"/media/orders/{order.id}"
            saved_paths = save_uploads(photos[:8], order_dir, url_prefix)

            if saved_paths:
                order.reference_photos = saved_paths
                order = self.repository.save(order)

        try:
            notifier = TelegramNotifier()
            items_str = "\n".join(
                [f"• {i.product_name} x {i.quantity}" for i in order.items]
            )

            notifier.send_message(
                f"🛍️ <b>¡Nueva Orden (ID: {order.id})!</b>\n\n"
                f"👤 <b>Instagram:</b> @{order.customer_instagram}\n"
                f"🗓️ <b>Fecha Entrega:</b> {order.delivery_date.strftime('%Y-%m-%d')}\n"
                f"📦 <b>Método:</b> {'Retiro' if order.delivery_method.value == 'pickup' else 'Delivery'}\n"
                f"📋 <b>Productos:</b>\n{items_str}\n"
                f"💰 <b>Total:</b> ${order.total_amount:,.0f}"
            )
        except Exception as e:
            logger.error("Failed to send Telegram notification: %s", e)

        return order

    def get_order(self, order_id: int) -> Optional[Order]:
        return self.repository.get_by_id(order_id)

    def list_orders(
        self,
        status: Optional[OrderStatus] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Order]:
        return self.repository.list_all(status=status, limit=limit, offset=offset)

    def update_order(self, order_id: int, data: OrderUpdateRequest) -> Optional[Order]:
        order = self.repository.get_by_id(order_id)
        if not order:
            return None

        order.delivery_date = data.delivery_date
        order.description = data.description
        order.delivery_method = data.delivery_method
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

        order_dir = os.path.join(
            os.environ["CONTAINER_MEDIA_PATH"], f"orders/{order_id}"
        )
        if os.path.exists(order_dir):
            shutil.rmtree(order_dir)
