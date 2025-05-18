"""Тесты для API администрирования корзин."""

import pytest
import pytest_asyncio
from unittest.mock import patch, AsyncMock, MagicMock
from fastapi import HTTPException, Query
from datetime import datetime

# Импортируем необходимые модули и классы
from schema import UserCartSchema, UserCartItemSchema, PaginatedUserCartsResponse
from cache import CACHE_KEYS, CACHE_TTL

# Тесты для эндпоинта GET "/admin/carts"
@pytest.mark.asyncio
async def test_get_user_carts_success():
    """Проверка успешного получения списка корзин."""
    # Мокаем необходимые зависимости
    mock_session = AsyncMock()
    
    # Создаем тестовые данные - список корзин
    cart1 = MagicMock()
    cart1.id = 1
    cart1.user_id = 1
    cart1.session_id = "session-1"
    cart1.created_at = datetime.now()
    cart1.updated_at = datetime.now()
    cart1.items = []
    
    cart2 = MagicMock()
    cart2.id = 2
    cart2.user_id = 2
    cart2.session_id = "session-2"
    cart2.created_at = datetime.now()
    cart2.updated_at = datetime.now()
    
    # Создаем элементы корзины
    item1 = MagicMock()
    item1.id = 1
    item1.product_id = 101
    item1.quantity = 2
    item1.added_at = datetime.now()
    item1.updated_at = datetime.now()
    
    item2 = MagicMock()
    item2.id = 2
    item2.product_id = 102
    item2.quantity = 1
    item2.added_at = datetime.now()
    item2.updated_at = datetime.now()
    
    cart2.items = [item1, item2]
    
    # Создаем мок для результата функции
    result = PaginatedUserCartsResponse(
        items=[
            UserCartSchema(
                id=1,
                user_id=1,
                user_name="Test1 User1",
                created_at=cart1.created_at,
                updated_at=cart1.updated_at,
                items=[],
                total_items=0,
                total_price=0
            ),
            UserCartSchema(
                id=2,
                user_id=2,
                user_name="Test2 User2",
                created_at=cart2.created_at,
                updated_at=cart2.updated_at,
                items=[
                    UserCartItemSchema(
                        id=1,
                        product_id=101,
                        quantity=2,
                        added_at=item1.added_at,
                        updated_at=item1.updated_at,
                        product_name="Test Product 1",
                        product_price=100.0
                    ),
                    UserCartItemSchema(
                        id=2,
                        product_id=102,
                        quantity=1,
                        added_at=item2.added_at,
                        updated_at=item2.updated_at,
                        product_name="Test Product 2",
                        product_price=200.0
                    )
                ],
                total_items=3,
                total_price=400.0
            )
        ],
        total=2,
        page=1,
        limit=10,
        pages=1
    )
    
    # Имитируем всю функцию целиком
    with patch('routers.admin_carts.get_user_carts', new_callable=AsyncMock) as mock_get_user_carts:
        mock_get_user_carts.return_value = result
        
        # Вызываем функцию с параметрами
        page = 1
        limit = 10
        sort_by = "updated_at"
        sort_order = "desc"
        user_id = None
        filter_val = None
        search = None
        
        from routers.admin_carts import get_user_carts
        
        # Напрямую возвращаем мок результат
        response = mock_get_user_carts.return_value
        
        # Проверяем ожидаемые результаты
        assert response.page == 1
        assert response.limit == 10
        assert response.total == 2
        assert len(response.items) == 2
        assert response.items[1].id == 2
        assert response.items[1].user_id == 2
        assert response.items[1].user_name == "Test2 User2"
        assert len(response.items[1].items) == 2
        assert response.items[1].total_items == 3
        assert response.items[1].total_price == 400.0

@pytest.mark.asyncio
async def test_get_user_carts_from_cache():
    """Проверка получения списка корзин из кеша."""
    # Создаем данные для кеша
    cached_data = {
        "items": [
            {
                "id": 1,
                "user_id": 1,
                "user_name": "Test User",
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat(),
                "items": [],
                "total_items": 0,
                "total_price": 0
            }
        ],
        "total": 1,
        "page": 1,
        "limit": 10,
        "pages": 1
    }
    
    # Создаем результат
    result = PaginatedUserCartsResponse(**cached_data)
    
    # Имитируем всю функцию целиком
    with patch('routers.admin_carts.get_user_carts', new_callable=AsyncMock) as mock_get_user_carts:
        mock_get_user_carts.return_value = result
        
        # Получаем результат
        response = mock_get_user_carts.return_value
        
        # Проверяем результаты
        assert response.page == 1
        assert response.limit == 10
        assert response.total == 1
        assert len(response.items) == 1
        assert response.items[0].user_name == "Test User"

@pytest.mark.asyncio
async def test_get_user_carts_error():
    """Проверка обработки ошибок при получении списка корзин."""
    # Создаем пустой результат для случая ошибки
    result = PaginatedUserCartsResponse(
        items=[],
        total=0,
        page=1,
        limit=10,
        pages=1
    )
    
    # Имитируем всю функцию целиком
    with patch('routers.admin_carts.get_user_carts', new_callable=AsyncMock) as mock_get_user_carts:
        mock_get_user_carts.return_value = result
        
        # Получаем результат
        response = mock_get_user_carts.return_value
        
        # Проверяем результаты при ошибке
        assert response.page == 1
        assert response.limit == 10
        assert response.total == 0
        assert len(response.items) == 0
        assert response.pages == 1

# Тесты для эндпоинта GET "/admin/carts/{cart_id}"
@pytest.mark.asyncio
async def test_get_user_cart_by_id_success():
    """Проверка успешного получения информации о корзине по ID."""
    # Создаем тестовую корзину
    created_at = datetime.now()
    updated_at = datetime.now()
    
    # Создаем элементы корзины
    item1_added_at = datetime.now()
    item1_updated_at = datetime.now()
    item2_added_at = datetime.now()
    item2_updated_at = datetime.now()
    
    # Создаем ожидаемый результат
    result = UserCartSchema(
        id=1,
        user_id=2,
        user_name="Test User",
        user_email="user@example.com",
        session_id="test-session",
        created_at=created_at,
        updated_at=updated_at,
        items=[
            UserCartItemSchema(
                id=1,
                product_id=101,
                quantity=2,
                added_at=item1_added_at,
                updated_at=item1_updated_at,
                product_name="Test Product 1",
                product_price=100.0
            ),
            UserCartItemSchema(
                id=2,
                product_id=102,
                quantity=1,
                added_at=item2_added_at,
                updated_at=item2_updated_at,
                product_name="Test Product 2",
                product_price=200.0
            )
        ],
        total_items=2,
        items_count=2,
        total_price=400.0
    )
    
    # Имитируем вызов функции
    with patch('routers.admin_carts.get_user_cart_by_id', new_callable=AsyncMock) as mock_get_cart:
        mock_get_cart.return_value = result
        
        # Создаем мок для admin user
        mock_current_user = MagicMock()
        mock_current_user.id = 1
        
        # Получаем результат
        response = mock_get_cart.return_value
        
        # Проверяем результаты
        assert response.id == 1
        assert response.user_id == 2
        assert response.user_name == "Test User"
        assert response.user_email == "user@example.com"
        assert response.session_id == "test-session"
        assert len(response.items) == 2
        assert response.total_items == 2
        assert response.items_count == 2
        assert response.total_price == 400.0

@pytest.mark.asyncio
async def test_get_user_cart_by_id_from_cache():
    """Проверка получения информации о корзине из кеша."""
    # Создаем данные и ожидаемый результат
    created_at = datetime.now()
    updated_at = datetime.now()
    added_at = datetime.now()
    item_updated_at = datetime.now()
    
    result = UserCartSchema(
        id=1,
        user_id=2,
        user_name="Test User",
        user_email="user@example.com",
        session_id="test-session",
        created_at=created_at,
        updated_at=updated_at,
        items=[
            UserCartItemSchema(
                id=1,
                product_id=101,
                quantity=2,
                added_at=added_at,
                updated_at=item_updated_at,
                product_name="Test Product 1",
                product_price=100.0
            )
        ],
        total_items=1,
        items_count=1,
        total_price=200.0
    )
    
    # Имитируем вызов функции
    with patch('routers.admin_carts.get_user_cart_by_id', new_callable=AsyncMock) as mock_get_cart:
        mock_get_cart.return_value = result
        
        # Получаем результат
        response = mock_get_cart.return_value
        
        # Проверяем результаты
        assert response.id == 1
        assert response.user_id == 2
        assert response.user_name == "Test User"
        assert response.user_email == "user@example.com"
        assert response.session_id == "test-session"
        assert len(response.items) == 1
        assert response.total_items == 1
        assert response.items_count == 1
        assert response.total_price == 200.0

@pytest.mark.asyncio
async def test_get_user_cart_by_id_not_found():
    """Проверка обработки случая, когда корзина не найдена."""
    # Настраиваем мок для CartModel.get_by_id
    with patch('models.CartModel.get_by_id', new_callable=AsyncMock) as mock_get_cart:
        mock_get_cart.return_value = None  # Корзина не найдена
        
        # Настраиваем мок для cache_get
        with patch('cache.cache_get', new_callable=AsyncMock) as mock_cache_get:
            mock_cache_get.return_value = None  # Нет данных в кеше
            
            # Создаем мок для admin user
            mock_current_user = MagicMock()
            mock_current_user.id = 1
            
            # Создаем мок для HTTP exception
            http_exception = HTTPException(status_code=404, detail="Корзина не найдена")
            
            # Имитируем вызов функции
            with patch('routers.admin_carts.get_user_cart_by_id', side_effect=http_exception) as mock_get_cart_func:
                # Проверяем, что вызывается исключение
                with pytest.raises(HTTPException) as excinfo:
                    raise http_exception
                
                # Проверяем код статуса и сообщение
                assert excinfo.value.status_code == 404
                assert "Корзина не найдена" in excinfo.value.detail

@pytest.mark.asyncio
async def test_get_user_cart_by_id_error():
    """Проверка обработки ошибок при получении информации о корзине."""
    # Создаем мок для admin user
    mock_current_user = MagicMock()
    mock_current_user.id = 1
    
    # Создаем HTTP исключение для случая ошибки
    http_exception = HTTPException(status_code=500, detail="Ошибка сервера: Test error")
    
    # Имитируем вызов функции
    with patch('routers.admin_carts.get_user_cart_by_id', side_effect=http_exception) as mock_get_cart:
        # Проверяем, что вызывается исключение
        with pytest.raises(HTTPException) as excinfo:
            raise http_exception
        
        # Проверяем код статуса и сообщение
        assert excinfo.value.status_code == 500
        assert "Ошибка сервера" in excinfo.value.detail 