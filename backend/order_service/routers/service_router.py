"""API эндпоинты сервиса заказов для внутренних сервисных запросов.
Предоставляет интерфейсы для взаимодействия между микросервисами."""

import logging
from typing import Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Path, status
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models import PromoCodeModel
from schemas import OrderDetailResponse, OrderDetailResponseWithPromo, PromoCodeResponse
from services import get_order_by_id
from dependencies import verify_service_jwt
from cache import CacheKeys, get_cached_data, set_cached_data, DEFAULT_CACHE_TTL

# Настройка логирования
logger = logging.getLogger("service_order_router")

# Создание роутера для сервисных запросов
router = APIRouter(
    prefix="/orders/service",
    tags=["service_orders"],
    responses={404: {"description": "Not found"}},
)

@router.get("/{order_id}", response_model=OrderDetailResponseWithPromo, dependencies=[Depends(verify_service_jwt)])
async def get_order_service(
    order_id: int = Path(..., ge=1),
    session: AsyncSession = Depends(get_db),
):
    """
    Получение информации о заказе для сервисных нужд.
    
    - **order_id**: ID заказа
    """
    try:
        # Для сервисного запроса используем простой ключ без user_id
        cache_key = f"{CacheKeys.ORDER_PREFIX}{order_id}:service"
        cached_order = await get_cached_data(cache_key)
        if cached_order:
            logger.info("Данные о заказе %s получены из кэша (сервисный запрос)", order_id)
            return cached_order
            
        # Получаем заказ без проверки на принадлежность пользователю
        order = await get_order_by_id(
            session=session,
            order_id=order_id,
            user_id=None  # Для сервисных запросов получаем заказ без проверки пользователя
        )
        
        if not order:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Заказ с ID {order_id} не найден",
            )
        
        # Преобразуем модель в схему без промокода
        order_response = OrderDetailResponse.model_validate(order)
        
        # Создаем расширенный ответ с возможностью добавления промокода
        response_with_promo = OrderDetailResponseWithPromo(**order_response.model_dump())
        
        # Получаем только последний статус, если история статусов существует
        if hasattr(response_with_promo, "status_history") and response_with_promo.status_history:
            # Сортируем историю статусов по дате изменения (вместо created_at используем changed_at)
            sorted_history = sorted(
                response_with_promo.status_history,
                key=lambda x: x.changed_at,
                reverse=True
            )
            response_with_promo.status_history = [sorted_history[0]] if sorted_history else []
        
        # Вручную обрабатываем промокод
        if order.promo_code_id:
            try:
                promo_code = await session.get(PromoCodeModel, order.promo_code_id)
                if promo_code:
                    response_with_promo.promo_code = PromoCodeResponse.model_validate(promo_code)
                    logger.info("Для заказа %s загружен промокод %s", order.id, promo_code.code)
            except (ValueError, AttributeError, KeyError) as e:
                logger.warning("Не удалось загрузить промокод %s для заказа %s: %s", order.promo_code_id, order.id, str(e))
        
        # Кэшируем результат со специальным ключом для сервисных запросов
        await set_cached_data(cache_key, response_with_promo, DEFAULT_CACHE_TTL)
        logger.info("Данные о заказе %s добавлены в кэш для сервисных запросов", order_id)
        
        return response_with_promo
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Ошибка при получении информации о заказе: %s", str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Произошла ошибка при получении информации о заказе",
        ) from e 