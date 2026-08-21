import logging
import os
import shutil
from datetime import datetime
from html import escape

from fastapi import UploadFile

from app.core.config import CONTAINER_MEDIA_PATH
from app.core.telegram import TelegramNotifier
from app.core.uploads import delete_media_files, save_uploads, update_photo_set
from app.modules.orders.cart import ParsedCart
from app.modules.orders.domain import DeliveryMethod, Order, OrderItem, OrderStatus
from app.modules.orders.repository import OrderRepository
from app.modules.orders.schemas import (
    OrderCreateRequest,
    OrderItemCreate,
    OrderUpdateRequest,
)

logger = logging.getLogger(__name__)


class OrderService:
    def __init__(self, repository: OrderRepository) -> None:
        self.repository = repository

    def create_order(
        self,
        data: OrderCreateRequest,
        photos: list[UploadFile],
        status: OrderStatus = OrderStatus.PENDING,
        amount_paid: int = 0,
        created_by_admin: bool = False,
    ) -> Order:
        items = [
            OrderItem(
                product_id=i.product_id, quantity=i.quantity, unit_price=i.unit_price
            )
            for i in data.items
        ]

        if status in (OrderStatus.PAID, OrderStatus.DELIVERED):
            amount_paid = data.total_amount
        else:
            amount_paid = max(0, min(amount_paid, data.total_amount))

        order = Order(
            customer_instagram=data.customer_instagram,
            delivery_date=data.delivery_date,
            availability_slot_id=data.availability_slot_id,
            description=data.description,
            delivery_method=data.delivery_method,
            total_amount=data.total_amount,
            amount_paid=amount_paid,
            items=items,
            status=status,
        )

        order = self.repository.save(order)

        if photos and photos[0].filename:
            order_dir = os.path.join(CONTAINER_MEDIA_PATH, f"orders/{order.id}")
            url_prefix = f"/media/orders/{order.id}"
            saved_paths = save_uploads(photos[:8], order_dir, url_prefix)

            if saved_paths:
                order.reference_photos = saved_paths
                order = self.repository.save(order)

        try:
            notifier = TelegramNotifier()
            # Dynamic fragments are HTML-parsed by Telegram, so escape them.
            items_str = "\n".join(
                [
                    f"• {escape(i.product_name or '')} x {i.quantity}"
                    for i in order.items
                ]
            )

            source = "📱 <i>(Creada por admin)</i>\n" if created_by_admin else ""

            notifier.send_message(
                f"🛍️ <b>¡Nueva Orden (ID: {order.id})!</b>\n"
                f"{source}\n"
                f"👤 <b>Instagram:</b> @{escape(order.customer_instagram)}\n"
                f"🗓️ <b>Fecha Entrega:</b> {order.delivery_date.strftime('%Y-%m-%d')}\n"
                f"📦 <b>Método:</b> {'Retiro' if order.delivery_method.value == 'pickup' else 'Delivery'}\n"
                f"📋 <b>Productos:</b>\n{items_str}\n"
                f"💰 <b>Total:</b> ${order.total_amount:,.0f}\n"
                f"💳 <b>Pagado:</b> ${order.amount_paid:,.0f}"
            )
        except Exception as e:  # noqa: BLE001 — Telegram is non-critical
            logger.error("Failed to send Telegram notification: %s", e)

        return order

    def create_from_parsed_cart(
        self,
        cart: ParsedCart,
        customer_instagram: str,
        delivery_date: datetime,
        availability_slot_id: int,
        delivery_method: DeliveryMethod,
        description: str,
        photos: list[UploadFile],
        status: OrderStatus = OrderStatus.PENDING,
        amount_paid: int = 0,
        created_by_admin: bool = False,
    ) -> Order:
        dto = OrderCreateRequest(
            customer_instagram=customer_instagram,
            items=cart.items,
            total_amount=cart.total_amount,
            delivery_date=delivery_date,
            availability_slot_id=availability_slot_id,
            delivery_method=delivery_method,
            description=description,
        )
        return self.create_order(
            data=dto,
            photos=photos,
            status=status,
            amount_paid=amount_paid,
            created_by_admin=created_by_admin,
        )

    def get_order(self, order_id: int) -> Order | None:
        return self.repository.get_by_id(order_id)

    def list_orders(
        self,
        include_closed: bool = False,
        limit: int = 100,
        offset: int = 0,
        sort_by: str | None = None,
        sort_dir: str = "desc",
    ) -> list[Order]:
        return self.repository.list_all(
            include_closed=include_closed,
            limit=limit,
            offset=offset,
            sort_by=sort_by,
            sort_dir=sort_dir,
        )

    def count_orders(self, include_closed: bool = False) -> int:
        return self.repository.count(include_closed)

    def update_order(
        self,
        order_id: int,
        data: OrderUpdateRequest,
        existing_photos: list[str],
        image_order: str,
        photos: list[UploadFile] | None,
    ) -> Order | None:
        order = self.repository.get_by_id(order_id)
        if not order:
            return None

        order.delivery_date = data.delivery_date
        order.availability_slot_id = data.availability_slot_id
        order.description = data.description
        order.delivery_method = data.delivery_method
        order.amount_paid = data.amount_paid

        current_photos = order.reference_photos or []
        order_dir = os.path.join(CONTAINER_MEDIA_PATH, f"orders/{order.id}")
        final_photos, removed = update_photo_set(
            current_urls=current_photos,
            existing_urls=existing_photos,
            image_order=image_order,
            photos=photos,
            max_images=8,
            media_dir=order_dir,
            url_prefix=f"/media/orders/{order.id}",
        )
        order.reference_photos = final_photos[:8]

        updated = self.repository.save(order)
        if updated is None:
            return None

        if removed:
            try:
                delete_media_files(order_dir, removed)
            except OSError:
                logger.warning("Failed to remove media files for order %d", order_id)

        return updated

    def change_status(self, order_id: int, new_status: OrderStatus) -> Order | None:
        order = self.repository.get_by_id(order_id)
        if not order:
            return None

        order.status = new_status
        if new_status in (OrderStatus.PAID, OrderStatus.DELIVERED):
            order.amount_paid = order.total_amount
        return self.repository.save(order)

    def update_order_items(
        self,
        order_id: int,
        items: list[OrderItemCreate],
        total_amount: int,
    ) -> Order | None:
        order = self.repository.get_by_id(order_id)
        if order is None:
            return None

        domain_items = [
            OrderItem(
                product_id=i.product_id,
                quantity=i.quantity,
                unit_price=i.unit_price,
            )
            for i in items
        ]

        amount_paid = min(order.amount_paid, total_amount)
        if order.status in (OrderStatus.PAID, OrderStatus.DELIVERED):
            amount_paid = total_amount

        return self.repository.replace_items(
            order_id, domain_items, total_amount, amount_paid
        )

    def delete_order(self, order_id: int) -> None:
        self.repository.delete(order_id)

        order_dir = os.path.join(CONTAINER_MEDIA_PATH, f"orders/{order_id}")
        if os.path.exists(order_dir):
            shutil.rmtree(order_dir)
