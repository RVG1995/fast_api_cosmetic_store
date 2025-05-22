"""API эндпоинты сервиса заказов для внутренних сервисных запросов.
Предоставляет интерфейсы для взаимодействия между микросервисами."""

import logging
from typing import Dict, Any,List
from fastapi import APIRouter, Depends, HTTPException, Path, status,Body
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, not_,text
from datetime import datetime

from database import get_db
from models import PromoCodeModel, OrderModel, DeliveryInfoModel, OrderStatusModel, BoxberryStatusFunnelModel, OrderStatusHistoryModel
from schemas import OrderDetailResponse, OrderDetailResponseWithPromo, PromoCodeResponse, BoxberryOrderResponse, BoxberryStatusUpdateRequest, BoxberryStatusUpdateResponse
from services import get_order_by_id
from dependencies import verify_service_jwt
from cache import CacheKeys, get_cached_data, set_cached_data, DEFAULT_CACHE_TTL
from config import settings

# Настройка логирования
logger = logging.getLogger("service_order_router")

# Создание роутера для сервисных запросов
router = APIRouter(
    prefix="/orders/service",
    tags=["service_orders"],
    responses={404: {"description": "Not found"}},
)

    

@router.get("/boxberry_delivery", response_model=List[BoxberryOrderResponse], dependencies=[Depends(verify_service_jwt)])
async def get_orders_service_boxberry_delivery(
    session: AsyncSession = Depends(get_db),
):
    """
    Получить все boxberry заказы, не отменённые и не доставленные, с tracking_number.
    Возвращает order_id и tracking_number.
    """
    try:
        # Получаем id статусов "Отменен" и "Доставлен"
        canceled_status = await session.execute(
            select(OrderStatusModel.id).where(OrderStatusModel.name == "Отменен")
        )
        delivered_status = await session.execute(
            select(OrderStatusModel.id).where(OrderStatusModel.name == "Доставлен")
        )
        canceled_id = canceled_status.scalar_one_or_none()
        delivered_id = delivered_status.scalar_one_or_none()

        # Делаем запрос
        query = (
            select(OrderModel.id, DeliveryInfoModel.tracking_number)
            .join(DeliveryInfoModel, DeliveryInfoModel.order_id == OrderModel.id)
            .where(
                DeliveryInfoModel.delivery_type.in_(["boxberry_pickup_point", "boxberry_courier"]),
                not_(OrderModel.status_id.in_([canceled_id, delivered_id])),
                DeliveryInfoModel.tracking_number.isnot(None),
                DeliveryInfoModel.tracking_number != ''
            )
        )
        result = await session.execute(query)
        orders = [BoxberryOrderResponse(order_id=row.id, tracking_number=row.tracking_number) for row in result.all()]
        return orders
    except Exception as e:
        logger.error("Ошибка при получении boxberry заказов: %s", str(e))
        raise HTTPException(status_code=500, detail="Ошибка при получении boxberry заказов") from e


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

@router.post("/boxberry_delivery/update_status", response_model=List[BoxberryStatusUpdateResponse], dependencies=[Depends(verify_service_jwt)])
async def update_boxberry_delivery_status(
    updates: List[BoxberryStatusUpdateRequest],
    session: AsyncSession = Depends(get_db),
):
    """
    Массовое обновление status_in_delivery_service для Boxberry по order_id и tracking_number.
    Вход: [{order_id, tracking_number, status_in_delivery_service}]
    Возвращает список с результатом для каждого заказа.
    """
    results = []
    for update in updates:
        query = select(DeliveryInfoModel).where(
            DeliveryInfoModel.order_id == update.order_id,
            DeliveryInfoModel.tracking_number == update.tracking_number
        )
        res = await session.execute(query)
        delivery_info = res.scalar_one_or_none()
        if delivery_info:
            delivery_info.status_in_delivery_service = update.status_in_delivery_service

            # --- ВОРОНКА: поддержка поиска по коду и по имени ---
            boxberry_status_name = update.status_in_delivery_service
            # 1. Пытаемся найти по имени
            funnel_rule = await session.execute(
                select(BoxberryStatusFunnelModel)
                .where(BoxberryStatusFunnelModel.boxberry_status_name == boxberry_status_name)
                .where(BoxberryStatusFunnelModel.active == True)
            )
            funnel = funnel_rule.scalar_one_or_none()
            # 2. Если не нашли по имени, ищем по коду (ищем код по имени через config)
            if not funnel:
                code = None
                for k, v in settings.BOXBERRY_STATUSES.items():
                    if v == boxberry_status_name:
                        code = k
                        break
                if code is not None:
                    funnel_rule = await session.execute(
                        select(BoxberryStatusFunnelModel)
                        .where(BoxberryStatusFunnelModel.boxberry_status_code == int(code))
                        .where(BoxberryStatusFunnelModel.active == True)
                    )
                    funnel = funnel_rule.scalar_one_or_none()
            if funnel:
                order = await session.get(OrderModel, update.order_id)
                if order and order.status_id != funnel.order_status_id:
                    order.status_id = funnel.order_status_id
                    order.updated_at = datetime.utcnow()
                    await OrderStatusHistoryModel.add_status_change(
                        session=session,
                        order_id=order.id,
                        status_id=funnel.order_status_id,
                        changed_by_user_id=None,
                        notes=f"Автоматически по Boxberry: {boxberry_status_name}"
                    )
            # --- КОНЕЦ ВОРОНКИ ---

            results.append(BoxberryStatusUpdateResponse(order_id=update.order_id, updated=True))
        else:
            results.append(BoxberryStatusUpdateResponse(order_id=update.order_id, updated=False))
    await session.commit()
    return results


@router.post("/check-can-review-store", status_code=status.HTTP_200_OK, dependencies=[Depends(verify_service_jwt)])
async def check_can_review_store(
    request_data: Dict[str, Any] = Body(...),
    session: AsyncSession = Depends(get_db)
):
    """
    Проверка, может ли пользователь оставить отзыв на магазин
    (имеет хотя бы один завершенный заказ)
    """
    try:
        user_id = request_data.get("user_id")
        
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Необходимо указать user_id"
            )
        
        # Проверяем, есть ли завершенные заказы у пользователя
        query = text("""
            SELECT COUNT(*) FROM orders o
            WHERE o.user_id = :user_id 
            AND o.status_id = 5
        """)
        
        result = await session.execute(query, {"user_id": user_id})
        count = result.scalar_one()
        
        return {"can_review": count > 0}
    except Exception as e:
        logger.error("Ошибка при проверке возможности оставить отзыв на магазин: %s", str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка при проверке возможности оставить отзыв на магазин"
        ) from e

@router.post("/check-can-review-product", status_code=status.HTTP_200_OK, dependencies=[Depends(verify_service_jwt)])
async def check_can_review_product(
    request_data: Dict[str, Any] = Body(...),
    session: AsyncSession = Depends(get_db)
):
    """
    Проверка, может ли пользователь оставить отзыв на товар
    (есть хотя бы один завершённый заказ с этим товаром)
    """
    try:
        user_id = request_data.get("user_id")
        product_id = request_data.get("product_id")
        if not user_id or not product_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Необходимо указать user_id и product_id"
            )
        # Проверяем, есть ли завершённые заказы с этим товаром у пользователя
        query = text("""
            SELECT COUNT(*) FROM order_items oi
            JOIN orders o ON oi.order_id = o.id
            WHERE o.user_id = :user_id
            AND o.status_id = 5
            AND oi.product_id = :product_id
        """)
        result = await session.execute(query, {"user_id": user_id, "product_id": product_id})
        count = result.scalar_one()
        return {"can_review": count > 0}
    except Exception as e:
        logger.error("Ошибка при проверке возможности оставить отзыв на товар: %s", str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка при проверке возможности оставить отзыв на товар"
        ) from e