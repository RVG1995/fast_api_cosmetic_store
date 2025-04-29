"""
Admin API endpoints for order management including listing, creation, and status updates.
"""

import os
import logging
from typing import List, Dict, Any
from datetime import datetime
import hashlib
from dotenv import load_dotenv
from fastapi import APIRouter, Depends, HTTPException, Path, status, Body
from fastapi.encoders import jsonable_encoder
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import SQLAlchemyError
from notification_api import check_notification_settings

from database import get_db
from models import OrderStatusModel, OrderStatusHistoryModel, PromoCodeModel
from schemas import (
    OrderCreate, OrderUpdate, OrderResponse, OrderDetailResponse,
    OrderStatusHistoryCreate, PaginatedResponse, OrderStatistics, BatchStatusUpdate,
    OrderItemsUpdate, OrderItemsUpdateResponse, PromoCodeResponse, OrderResponseWithPromo, OrderDetailResponseWithPromo,
    AdminOrderCreate
)
from services import (
    create_order, get_order_by_id, get_orders, update_order,
    change_order_status, get_order_statistics,
    update_order_items
)
from dependencies import (
    get_admin_user, get_order_filter_params,
    check_products_availability
)
from cache import (
    get_cached_order, cache_order, invalidate_order_cache,
    get_cached_order_statistics, cache_order_statistics, invalidate_statistics_cache,
    get_cached_orders_list, cache_orders_list
)

# Загрузка переменных окружения
load_dotenv()

# Настройка логирования
logger = logging.getLogger("admin_order_router")

# Получение URL сервиса продуктов
PRODUCT_SERVICE_URL = os.getenv("PRODUCT_SERVICE_URL", "http://localhost:8001")

# Создание роутера для админ-панели
admin_router = APIRouter(
    prefix="/admin/orders",
    tags=["admin_orders"],
    responses={404: {"description": "Not found"}},
)

@admin_router.get("", response_model=PaginatedResponse)
async def list_all_orders(
    filters = Depends(get_order_filter_params),
    current_user: Dict[str, Any] = Depends(get_admin_user),
    session: AsyncSession = Depends(get_db)
):
    """
    Получение списка всех заказов (только для администраторов).

    Поддерживает фильтрацию по различным параметрам.
    """
    try:
        # Проверка, что пользователь является администратором
        if not current_user or not current_user.get("is_admin"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Доступ запрещен. Требуются права администратора."
            )

        # Создаем ключ для кэша на основе параметров фильтрации
        filter_params = filters.model_dump_json()
        cache_key = hashlib.md5(filter_params.encode()).hexdigest()

        # Пытаемся получить данные из кэша
        cached_orders = await get_cached_orders_list(cache_key)
        if cached_orders:
            logger.info("Данные о всех заказах получены из кэша по ключу %s", cache_key)
            return cached_orders

        # Если данных нет в кэше, получаем из БД
        orders, total = await get_orders(
            session=session,
            filters=filters
        )

        # Формируем ответ с преобразованием моделей в схемы
        order_responses = []
        for order in orders:
            # Создаем базовый объект OrderResponse без промокода
            order_response = OrderResponse.model_validate(order)

            # Если у заказа есть промокод, создаем OrderResponseWithPromo
            if order.promo_code_id:
                # Создаем расширенный ответ с информацией о промокоде
                with_promo = OrderResponseWithPromo(**order_response.model_dump())

                try:
                    # Получаем промокод и устанавливаем его
                    promo_code = await session.get(PromoCodeModel, order.promo_code_id)
                    if promo_code:
                        with_promo.promo_code = PromoCodeResponse.model_validate(promo_code)
                        logger.info(
                            "Для заказа %s загружен промокод %s (в админ списке)", 
                            order.id, promo_code.code
                        )
                except SQLAlchemyError as e:
                    logger.warning("Не удалось загрузить промокод %s для заказа %s: %s",
                     order.promo_code_id, order.id, str(e))

                order_responses.append(with_promo)
            else:
                # Заказ без промокода, используем обычный OrderResponse
                order_responses.append(order_response)

        response = PaginatedResponse(
            items=order_responses,
            total=total,
            page=filters.page,
            size=filters.size,
            pages=0  # Будет вычислено в валидаторе
        )

        # Кэшируем результат
        await cache_orders_list(cache_key, response)
        logger.info("Данные о всех заказах добавлены в кэш по ключу %s", cache_key)

        return response
    except SQLAlchemyError as e:
        logger.error("Ошибка базы данных при получении списка заказов: %s", str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка базы данных при получении списка заказов",
        ) from e
    except ValueError as e:
        logger.error("Ошибка валидации при получении списка заказов: %s", str(e))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e
    except Exception as e:
        logger.error("Непредвиденная ошибка при получении списка заказов: %s", str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Произошла ошибка при получении списка заказов",
        ) from e

@admin_router.get("/statistics", response_model=OrderStatistics)
async def get_admin_orders_statistics(
    session: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_admin_user)
):
    """
    Получение статистики по всем заказам (только для администраторов)
    """
    try:
        # Проверка, что пользователь является администратором
        if not current_user or not current_user.get("is_admin"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Доступ запрещен. Требуются права администратора."
            )
        # Пытаемся получить данные из кэша
        cached_statistics = await get_cached_order_statistics()
        if cached_statistics:
            logger.info("Статистика всех заказов получена из кэша")
            return cached_statistics

        # Если данных нет в кэше, получаем из БД
        statistics = await get_order_statistics(session)

        # Кэшируем результат
        await cache_order_statistics(statistics)
        logger.info("Статистика всех заказов добавлена в кэш")

        return statistics
    except SQLAlchemyError as e:
        logger.error("Ошибка базы данных при получении статистики заказов: %s", str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка базы данных при получении статистики заказов"
        ) from e
    except Exception as e:
        logger.error("Непредвиденная ошибка при получении статистики заказов: %s", str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка при получении статистики заказов"
        ) from e

@admin_router.get("/{order_id}", response_model=OrderDetailResponseWithPromo)
async def get_order_admin(
    order_id: int = Path(..., ge=1),
    current_user: Dict[str, Any] = Depends(get_admin_user),
    session: AsyncSession = Depends(get_db)
):
    """
    Получение информации о заказе по ID (только для администраторов)

    - **order_id**: ID заказа
    """
    try:
        # Проверка, что пользователь является администратором
        if not current_user or not current_user.get("is_admin"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Доступ запрещен. Требуются права администратора."
            )
        # Пытаемся получить данные из кэша
        cached_order = await get_cached_order(order_id, admin=True)
        if cached_order:
            logger.info("Данные о заказе %s получены из кэша (админ)", order_id)
            return cached_order

        # Получаем заказ
        order = await get_order_by_id(session, order_id)

        if not order:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Заказ с ID {order_id} не найден",
            )

        # Преобразуем модель в схему без промокода
        order_response = OrderDetailResponse.model_validate(order)

        # Создаем расширенный ответ с возможностью добавления промокода
        response_with_promo = OrderDetailResponseWithPromo(**order_response.model_dump())

        # Вручную обрабатываем промокод
        if order.promo_code_id:
            try:
                promo_code = await session.get(PromoCodeModel, order.promo_code_id)
                if promo_code:
                    response_with_promo.promo_code = PromoCodeResponse.model_validate(promo_code)
                    logger.info("Для заказа %s загружен промокод %s (админ)",
                     order.id, promo_code.code)
            except SQLAlchemyError as e:
                logger.warning("Не удалось загрузить промокод %s для заказа %s: %s",
                 order.promo_code_id, order.id, str(e))

        # Кэшируем результат
        await cache_order(order_id, response_with_promo, admin=True)
        logger.info("Данные о заказе %s добавлены в кэш (админ)", order_id)

        return response_with_promo
    except SQLAlchemyError as e:
        logger.error("Ошибка базы данных при получении информации о заказе (админ): %s", str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка базы данных при получении информации о заказе",
        ) from e
    except ValueError as e:
        logger.error("Ошибка валидации при получении информации о заказе (админ): %s", str(e))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e
    except Exception as e:
        logger.error("Непредвиденная ошибка при получении информации о заказе (админ): %s", str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Произошла ошибка при получении информации о заказе",
        ) from e

@admin_router.put("/{order_id}", response_model=OrderResponse)
async def update_order_admin(
    order_id: int = Path(..., ge=1),
    order_data: OrderUpdate = Body(...),
    current_user: Dict[str, Any] = Depends(get_admin_user),
    session: AsyncSession = Depends(get_db)
):
    """
    Обновление информации о заказе (только для администраторов).

    - **order_id**: ID заказа
    - **order_data**: Данные для обновления
    """
    try:
        # Обновляем заказ
        order = await update_order(
            session=session,
            order_id=order_id,
            order_data=order_data
        )

        if not order:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Заказ с ID {order_id} не найден",
            )

        # Добавляем запись в историю статусов, если статус был изменен
        if order_data.status_id is not None:
            # Используем комментарий, если он предоставлен, иначе используем стандартное сообщение
            status_note = (
                order_data.comment
                if order_data.comment
                else "Статус обновлен администратором"
            )

            await OrderStatusHistoryModel.add_status_change(
                session=session,
                order_id=order.id,
                status_id=order_data.status_id,
                changed_by_user_id=current_user["user_id"],
                notes=status_note
            )

        # Коммитим сессию
        await session.commit()

        # Вручную запрашиваем заказ со всеми связанными данными
        loaded_order = await get_order_by_id(session, order.id)

        # Инвалидируем кэш заказа
        await invalidate_order_cache(order_id)
        # Инвалидируем кэш статистики, если изменился статус
        if order_data.status_id is not None:
            await invalidate_statistics_cache()
        logger.info("Кэш заказа %s инвалидирован после обновления заказа", order_id)

        # Преобразуем модель в схему
        return OrderResponse.model_validate(loaded_order)
    except ValueError as e:
        logger.error("Ошибка при обновлении заказа: %s", str(e))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e
    except Exception as e:
        logger.error("Непредвиденная ошибка при обновлении заказа: %s", str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Произошла ошибка при обновлении заказа",
        ) from e

@admin_router.post("/{order_id}/status", response_model=OrderResponse)
async def update_order_status(
    order_id: int = Path(..., ge=1),
    status_data: dict = Body(...),
    current_user: Dict[str, Any] = Depends(get_admin_user),
    session: AsyncSession = Depends(get_db)
):
    """
    Обновление статуса заказа (только для администраторов).
    Упрощенный эндпоинт для обновления только статуса.

    - **order_id**: ID заказа
    - **status_data**: Данные о новом статусе:
      - status_id: ID нового статуса
      - comment: Комментарий к изменению статуса (опционально)
    """
    try:
        logger.info("Запрос на обновление статуса заказа. ID: %s, данные: %s",
         order_id, status_data)
        # Проверка, что пользователь является администратором
        if not current_user or not current_user.get("is_admin"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Доступ запрещен. Требуются права администратора."
            )

        # Проверяем наличие обязательного поля status_id
        if not status_data.get("status_id"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Не указан ID статуса",
            )

        # Создаем объект OrderUpdate только с нужными полями
        status_id = status_data.get("status_id")
        comment = status_data.get("comment")

        # Проверяем, что статус существует
        status_name = await session.get(OrderStatusModel, status_id)
        if not status_name:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Статус с ID {status_id} не найден",
            )

        # Получаем текущий заказ
        order = await get_order_by_id(session, order_id)
        if not order:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Заказ с ID {order_id} не найден",
            )

        # Обновляем статус заказа
        order.status_id = status_id
        session.add(order)

        # Добавляем запись в историю статусов
        status_note = comment if comment else "Статус обновлен администратором"
        await OrderStatusHistoryModel.add_status_change(
            session=session,
            order_id=order_id,
            status_id=status_id,
            changed_by_user_id=current_user["user_id"],
            notes=status_note
        )

        # Получаем информацию о новом статусе
        new_status = await session.get(OrderStatusModel, status_id)
        new_status_name = new_status.name if new_status else "Неизвестный"

        # Получаем информацию о старом статусе
        old_status = await session.get(OrderStatusModel, order.status_id)
        old_status_name = old_status.name if old_status else "Неизвестный"

        # Фиксируем изменения в базе данных
        await session.commit()

        # Инвалидируем кэш заказа
        await invalidate_order_cache(order_id)
        # Инвалидируем кэш статистики
        await invalidate_statistics_cache()
        logger.info(
            "Кэш заказа %s и статистики инвалидирован после изменения статуса с '%s' на '%s'",
            order_id, old_status_name, new_status_name
        )

        # Обновляем заказ в сессии
        updated_order = await get_order_by_id(session, order_id)

        # Если у заказа есть промокод, загружаем его ПЕРЕД отправкой уведомления
        if updated_order.promo_code_id:
            # Загружаем промокод
            promo_code = await session.get(PromoCodeModel, updated_order.promo_code_id)
            if promo_code:
                # Создаем словарь с данными промокода для передачи в RabbitMQ
                updated_order.promo_code_dict = {
                    "code": promo_code.code,
                    "discount_percent": promo_code.discount_percent or 0
                }
                logger.info("Для заказа %s загружен промокод %s (при обновлении статуса)",
                           updated_order.id, promo_code.code)

        # Отправляем уведомление об изменении статуса через Notifications Service
        try:
            # Подготавливаем payload: убираем историю статусов и обновляем статус
            payload = jsonable_encoder(updated_order, exclude={'status_history'})
            payload.pop('status', None)
            payload['status'] = new_status_name
            if updated_order.email:
                await check_notification_settings(
                    updated_order.user_id,
                    "order.status_changed",
                    payload
                )
            logger.info("Отправлено событие 'order.status_changed' для заказа %s", order_id)
        except (ConnectionError, TimeoutError) as e:
            logger.error("Ошибка соединения при отправке события изменения статуса: %s", e)
        except (ValueError, TypeError, AttributeError) as e:
            logger.error("Ошибка данных при отправке события изменения статуса: %s", e)

        return OrderResponse.model_validate(updated_order)
    except SQLAlchemyError as e:
        logger.error("Ошибка при обновлении статуса заказа: %s", str(e))
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Произошла ошибка при обновлении статуса заказа: {str(e)}",
        ) from e
    except (ValueError, TypeError, AttributeError) as e:
        logger.error("Ошибка валидации при обновлении статуса заказа: %s", str(e))
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Ошибка при обновлении статуса заказа: {str(e)}",
        ) from e

@admin_router.post("/{order_id}/items", response_model=OrderItemsUpdateResponse)
async def update_order_items_endpoint(
    order_id: int,
    items_data: OrderItemsUpdate,
    session: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_admin_user)
):
    """Обновление товаров в заказе (админский доступ)"""
    logger.info(
        "Запрос на обновление элементов заказа %s:"
        " items_to_add=%s items_to_update=%s items_to_remove=%s",
        order_id, items_data.items_to_add, items_data.items_to_update, items_data.items_to_remove
    )

    try:
        # Проверка, что пользователь является администратором
        if not current_user or not current_user.get("is_admin"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Доступ запрещен. Требуются права администратора."
            )
        # Получаем текущий статус заказа
        order = await get_order_by_id(session, order_id)
        if not order:
            raise HTTPException(status_code=404, detail="Заказ не найден")

        # Проверка статуса заказа - запрещаем редактировать товары для определенных статусов
        non_editable_statuses = ["Отправлен", "Доставлен", "Отменен", "Оплачен"]
        if order.status and order.status.name in non_editable_statuses:
            raise HTTPException(
                status_code=400,
                detail=(f"Редактирование товаров невозможно для заказа "
                       f"в статусе '{order.status.name}'")
            )

        # Подготавливаем данные для обновления
        items_to_add = (
            [item.model_dump() for item in items_data.items_to_add]
            if items_data.items_to_add else []
        )
        items_to_update = items_data.items_to_update if items_data.items_to_update else {}
        items_to_remove = items_data.items_to_remove if items_data.items_to_remove else []

        # Вызываем сервисную функцию
        updated_order = await update_order_items(
            order_id=order_id,
            items_to_add=items_to_add,
            items_to_update=items_to_update,
            items_to_remove=items_to_remove,
            session=session,
            user_id=int(current_user.get("sub")) if current_user.get("sub") else None
        )

        if not updated_order:
            raise HTTPException(status_code=400, detail="Ошибка при обновлении элементов заказа")

        # Создаем ответ с данными заказа
        order_dict = {
            "id": updated_order.id,
            "user_id": updated_order.user_id,
            "status_id": updated_order.status_id,
            "status": {
                "id": updated_order.status.id,
                "name": updated_order.status.name,
                "description": updated_order.status.description,
                "color": updated_order.status.color,
                "allow_cancel": updated_order.status.allow_cancel,
                "is_final": updated_order.status.is_final,
                "sort_order": updated_order.status.sort_order
            },
            "created_at": updated_order.created_at,
            "updated_at": datetime.now(),
            "total_price": updated_order.total_price,
            "promo_code_id": updated_order.promo_code_id,
            "discount_amount": updated_order.discount_amount,
            "full_name": updated_order.full_name,
            "email": updated_order.email,
            "phone": updated_order.phone,
            "region": updated_order.region,
            "city": updated_order.city,
            "street": updated_order.street,
            "comment": updated_order.comment,
            "is_paid": updated_order.is_paid,
            "items": [
                {
                    "id": item.id,
                    "order_id": item.order_id,
                    "product_id": item.product_id,
                    "product_name": item.product_name,
                    "product_price": item.product_price,
                    "quantity": item.quantity,
                    "total_price": item.total_price
                }
                for item in updated_order.items
            ],
            "order_number": f"{updated_order.id}-{updated_order.created_at.year}"
        }

        # Добавляем данные о промокоде, если он есть
        if hasattr(updated_order, 'promo_code') and updated_order.promo_code:
            promo = updated_order.promo_code
            order_dict["promo_code"] = {
                "id": promo.id,
                "code": promo.code,
                "discount_percent": promo.discount_percent,
                "discount_amount": promo.discount_amount,
                "valid_until": promo.valid_until,
                "is_active": promo.is_active,
                "created_at": promo.created_at,
                "updated_at": datetime.now()
            }

        return OrderItemsUpdateResponse(success=True, order=order_dict)
    except SQLAlchemyError as e:
        logger.error("Ошибка базы данных при обновлении элементов заказа: %s", str(e))
        return OrderItemsUpdateResponse(
            success=False,
            errors={"message": f"Ошибка базы данных при обновлении элементов заказа: {str(e)}"}
        )
    except (ValueError, TypeError, AttributeError) as e:
        logger.error("Ошибка данных при обновлении элементов заказа: %s", str(e))
        return OrderItemsUpdateResponse(
            success=False,
            errors={"message": f"Ошибка при обновлении элементов заказа: {str(e)}"}
        )
    except (IOError, OSError) as e:
        logger.error("Ошибка ввода-вывода при обновлении элементов заказа: %s", str(e))
        return OrderItemsUpdateResponse(
            success=False,
            errors={"message": f"Системная ошибка при обновлении элементов заказа: {str(e)}"}
        )

@admin_router.post("/batch-status", response_model=List[OrderResponse])
async def update_batch_status(
    update_data: BatchStatusUpdate,
    current_user: Dict[str, Any] = Depends(get_admin_user),
    session: AsyncSession = Depends(get_db)
):
    """
    Обновление статуса для нескольких заказов одновременно (только для администраторов).

    - **update_data**: Данные для массового обновления статусов
    """
    try:
        # Проверка, что пользователь является администратором
        if not current_user or not current_user.get("is_admin"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Доступ запрещен. Требуются права администратора."
            )
        # Проверяем существование статуса
        status_record = await session.get(OrderStatusModel, update_data.status_id)
        if not status_record:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Статус с ID {update_data.status_id} не найден",
            )

        updated_orders = []
        for order_id in update_data.order_ids:
            try:
                # Создаем данные для обновления
                order_data = OrderUpdate(status_id=update_data.status_id)

                # Обновляем заказ
                order = await update_order(
                    session=session,
                    order_id=order_id,
                    order_data=order_data
                )

                if order:
                    # Добавляем запись в историю статусов
                    await OrderStatusHistoryModel.add_status_change(
                        session=session,
                        order_id=order.id,
                        status_id=update_data.status_id,
                        changed_by_user_id=current_user["user_id"],
                        notes=update_data.notes or "Массовое обновление статуса"
                    )

                    loaded_order = await get_order_by_id(session, order.id)
                    updated_orders.append(loaded_order)
            except (SQLAlchemyError, ValueError) as e:
                logger.error("Ошибка при обновлении заказа %s: %s", order_id, str(e))
                # Продолжаем с другими заказами

        # Коммитим сессию
        await session.commit()

        # Преобразуем модели в схемы
        return [OrderResponse.model_validate(order) for order in updated_orders]
    except SQLAlchemyError as e:
        logger.error("Непредвиденная ошибка при массовом обновлении статусов: %s", str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Произошла ошибка при массовом обновлении статусов",
        ) from e
    except (ValueError, TypeError, KeyError) as e:
        logger.error("Ошибка валидации при массовом обновлении статусов: %s", str(e))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Ошибка валидации при массовом обновлении статусов: {str(e)}",
        ) from e

@admin_router.post("", response_model=OrderResponseWithPromo, status_code=status.HTTP_201_CREATED)
async def create_order_admin(
    order_data: AdminOrderCreate,
    current_user: Dict[str, Any] = Depends(get_admin_user),
    session: AsyncSession = Depends(get_db)
):
    """
    Создание нового заказа из админки. Доступно только для администраторов.

    - **order_data**: Данные для создания заказа
    """
    try:
        # Проверка, что пользователь является администратором
        if not current_user or not current_user.get("is_admin"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Доступ запрещен. Требуются права администратора."
            )
        logger.info("Получен запрос на создание заказа из админки: %s", order_data)

        # Получаем токен авторизации администратора для запросов к другим сервисам
        token = current_user.get("token")

        # Если передан user_id, используем его, иначе заказ создается без привязки к пользователю
        user_id = order_data.user_id

        # Обработка пустого промокода
        promo_code = order_data.promo_code
        if promo_code == "" or (promo_code and len(promo_code) < 3):
            promo_code = None

        # Нормализация телефона
        phone = order_data.phone
        # Добавляем префикс, если его нет
        if phone and not (phone.startswith('8') or phone.startswith('+7')):
            phone = '8' + phone

        # Убеждаемся, что телефон имеет нужную длину
        if phone and len(phone) < 11:
            if phone.startswith('8'):
                # Дополняем до 11 цифр для формата 8XXXXXXXXXX
                missing_digits = 11 - len(phone)
                if missing_digits > 0:
                    phone = phone + '0' * missing_digits
            elif phone.startswith('+7'):
                # Дополняем до 12 цифр для формата +7XXXXXXXXXX
                missing_digits = 12 - len(phone)
                if missing_digits > 0:
                    phone = phone + '0' * missing_digits

        # Преобразуем данные из AdminOrderCreate в OrderCreate
        create_data = OrderCreate(
            items=order_data.items,
            full_name=order_data.full_name,
            email=order_data.email,
            phone=phone,  # Используем нормализованный телефон
            region=order_data.region,
            city=order_data.city,
            street=order_data.street,
            comment=order_data.comment,
            promo_code=promo_code,  # Используем обработанный промокод
            personal_data_agreement=True  # Для админа всегда True
        )

        # Проверяем наличие товаров
        product_ids = [item.product_id for item in order_data.items]
        availability = await check_products_availability(product_ids, token)

        # Проверяем, все ли товары доступны
        unavailable_products = [pid for pid, available in availability.items() if not available]
        if unavailable_products:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Товары с ID {unavailable_products} недоступны для заказа",
            )

        # Создаем заказ через общую функцию
        order = await create_order(
            session=session,
            user_id=user_id,
            order_data=create_data,
            product_service_url=PRODUCT_SERVICE_URL,
            token=token
        )

        # Если указан начальный статус и он отличается от дефолтного
        if order_data.status_id:
            try:
                status_data = OrderStatusHistoryCreate(
                    status_id=order_data.status_id,
                    notes="Статус установлен при создании заказа администратором"
                )
                order = await change_order_status(
                    session=session,
                    order_id=order.id,
                    status_data=status_data,
                    user_id=current_user["user_id"],
                    is_admin=True
                )
                logger.info("Для нового заказа %s установлен статус %s",
                order.id, order_data.status_id)
            except (SQLAlchemyError, ValueError) as e:
                logger.warning("Не удалось установить начальный статус %s для заказа %s: %s",
                              order_data.status_id, order.id, str(e))

        # Устанавливаем флаг оплаты, если указан
        if order_data.is_paid:
            order.is_paid = True
            await session.commit()
            logger.info("Для нового заказа %s установлен флаг оплаты", order.id)

        # Явно коммитим сессию, чтобы убедиться, что все связанные данные загружены
        await session.commit()

        # Вручную запрашиваем заказ со всеми связанными данными
        loaded_order = await get_order_by_id(session, order.id)

        # Если у заказа есть промокод, загружаем его
        if loaded_order.promo_code_id:
            # Загружаем промокод
            promo_code = await session.get(PromoCodeModel, loaded_order.promo_code_id)
            if promo_code:
                # Создаем словарь с данными промокода для передачи в RabbitMQ
                loaded_order.promo_code_dict = {
                    "code": promo_code.code,
                    "discount_percent": promo_code.discount_percent or 0
                }
                logger.info(
                    "Для заказа %s загружен промокод %s (в админ списке)", 
                    order.id, promo_code.code
                )

        # Отправляем подтверждение заказа на email через Notifications Service
        try:
            if order_data.email and user_id is not None:
                logger.info("Отправка подтверждения заказа на email: %s", order_data.email)
                # CONVERT loaded_order to plain dict for JSON payload
                payload = jsonable_encoder(loaded_order)
                await check_notification_settings(loaded_order.user_id, "order.created", payload)
        except (ConnectionError, TimeoutError) as e:
            logger.error("Ошибка соединения при отправке email о заказе: %s", str(e))
        except (ValueError, TypeError) as e:
            logger.error("Ошибка данных при отправке email о заказе: %s", str(e))

        # Явно инвалидируем кэш заказов перед возвратом ответа
        await invalidate_order_cache(order.id)
        logger.info("Кэш заказа %s и связанных списков инвалидирован перед возвратом ответа",
        order.id)

        # Преобразуем модель в схему без промокода
        order_response = OrderResponse.model_validate(loaded_order)

        # Создаем расширенный ответ с возможностью добавления промокода
        response_with_promo = OrderResponseWithPromo(**order_response.model_dump())

        # Если у заказа есть промокод, загружаем его данные вручную
        if loaded_order.promo_code_id:
            try:
                promo_code = await session.get(PromoCodeModel, loaded_order.promo_code_id)
                if promo_code:
                    response_with_promo.promo_code = PromoCodeResponse.model_validate(promo_code)
                    logger.info("Для нового заказа %s загружен промокод %s",
                    loaded_order.id, promo_code.code)
            except (SQLAlchemyError, AttributeError) as e:
                logger.warning("Не удалось загрузить промокод %s для заказа %s: %s",
                             loaded_order.promo_code_id, loaded_order.id, str(e))

        return response_with_promo
    except ValueError as e:
        logger.error("Ошибка при создании заказа из админки: %s", str(e))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e
    except SQLAlchemyError as e:
        logger.error("Ошибка базы данных при создании заказа из админки: %s", str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка базы данных при создании заказа",
        ) from e
    except (TypeError, AttributeError, KeyError) as e:
        logger.error("Ошибка данных при создании заказа из админки: %s", str(e))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Ошибка входных данных: {str(e)}",
        ) from e
