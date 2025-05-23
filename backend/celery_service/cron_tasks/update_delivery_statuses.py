import logging
import os
import sys
from pathlib import Path
import httpx

import asyncio

from config import settings
from dependencies import _get_service_token

logger = logging.getLogger("order_service.notification_api")

# URL сервисов из конфигурации
NOTIFICATION_SERVICE_URL = settings.NOTIFICATION_SERVICE_URL
AUTH_SERVICE_URL = settings.AUTH_SERVICE_URL
ORDER_SERVICE_URL = settings.ORDER_SERVICE_URL

# Добавляем родительскую директорию в sys.path, если её ещё нет
current_dir = Path(__file__).parent.absolute()
parent_dir = current_dir.parent
if str(parent_dir) not in sys.path:
    sys.path.insert(0, str(parent_dir))


logger = logging.getLogger(__name__)
async def get_orders_service_boxberry_delivery():
    """
    Проверяет настройки уведомлений пользователя для указанного типа события
    
    Args:
        user_id: ID пользователя
        event_type: Тип события (например, "order.created", "order.status_changed")
        token: JWT токен для авторизации в сервисе уведомлений
        
    Returns:
        Словарь с флагами настроек {email_enabled: bool, push_enabled: bool}
        Если произошла ошибка - возвращает {email_enabled: False, push_enabled: False}
    """
    try:
        # perform with retry on 401
        backoffs = [0.5, 1, 2]
        async with httpx.AsyncClient() as client:
            for delay in backoffs:
                token = await _get_service_token()
                headers = {"Authorization": f"Bearer {token}"}
                orders_response = await client.get(
                    f"{ORDER_SERVICE_URL}/orders/service/boxberry_delivery",
                    headers=headers, timeout=5.0,
                )
                if orders_response.status_code == 401:
                    # token expired - clear cache and retry
                    await asyncio.sleep(delay)
                    continue
                break
            if orders_response.status_code == 200:
                return orders_response.json()
            elif orders_response.status_code == 404:
                # Настройки не найдены, используем значения по умолчанию
                logger.info("Заказов для обновления статусов не найдено")
                return []
            else:
                logger.warning("Ошибка при получении заказов для обновления статусов: %s, %s", orders_response.status_code, orders_response.text)
                return {"warning": False}
                
    except (httpx.HTTPError, httpx.TimeoutException, httpx.RequestError) as e:
        logger.error("Ошибка при запросе настроек уведомлений: %s", str(e))

async def fetch_boxberry_statuses(tracking_numbers: list[str]) -> dict[str, str]:
    """
    Возвращает dict: tracking_number -> lastStatusName
    """
    payload = {
        "token": settings.BOXBERRY_TOKEN,
        "method": "GetLastStatusData",
        "trackNumbers": tracking_numbers,
    }
    async with httpx.AsyncClient() as client:
        resp = await client.post(settings.BOXBERRY_API_URL, json=payload, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        logger.info(f"Ответ Boxberry: {data}")
        # Boxberry может вернуть {'err': ...} или {'result': ...}
        if isinstance(data, dict):
            # Boxberry иногда возвращает {'err': ...} или {'data': [...]}
            if "err" in data:
                logger.error(f"Ошибка Boxberry: {data['err']}")
                return {}
            if "data" in data:
                data = data["data"]
            elif "result" in data:
                data = data["result"]
            else:
                logger.error(f"Неожиданный формат ответа Boxberry: {data}")
                return {}
        if not isinstance(data, list):
            logger.error(f"Ожидался список, а пришло: {type(data)}")
            return {}
        return {item["trackNumber"]: item.get("lastStatusName") for item in data if "trackNumber" in item}

async def update_order_statuses(status_updates: list[dict]):
    """
    Отправляет массовое обновление статусов в order_service.
    status_updates: [{order_id, tracking_number, status_in_delivery_service}]
    """
    async with httpx.AsyncClient() as client:
        resp = await client.post(f"{ORDER_SERVICE_URL}/orders/service/boxberry_delivery/update_status", json=status_updates, timeout=10)
        resp.raise_for_status()
        return resp.json()

async def cron_update_boxberry_statuses():
    # 1. Получаем заказы с boxberry доставкой
    orders = await get_orders_service_boxberry_delivery()  # [{order_id, tracking_number}]
    if not orders:
        logger.info("Нет заказов для обновления статусов Boxberry")
        return

    # 2. Собираем все трек-номера
    tracking_numbers = [order["tracking_number"] for order in orders]

    # 3. Получаем статусы из Boxberry
    status_map = await fetch_boxberry_statuses(tracking_numbers)
    logger.info(f"Получены статусы из Boxberry: {status_map}")

    # 4. Формируем список для обновления в order_service
    updates = []
    for order in orders:
        tracking_number = order["tracking_number"]
        status = status_map.get(tracking_number)
        if status:
            updates.append({
                "order_id": order["order_id"],
                "tracking_number": tracking_number,
                "status_in_delivery_service": status,
            })

    if not updates:
        logger.info("Нет статусов для обновления в order_service")
        return

    # 5. Массово обновляем статусы в order_service
    result = await update_order_statuses(updates)
    logger.info(f"Результат обновления статусов в order_service: {result}")