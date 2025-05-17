"""Тесты для модуля административных эндпоинтов (admin_router.py)."""

import sys
import os
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

# Импортируем модули для тестирования
from admin_router import router, verify_service_key
from models import UserModel

# Фикстуры для тестирования
@pytest.fixture
def mock_session():
    """Мок для сессии базы данных"""
    return AsyncMock(spec=AsyncSession)

@pytest.fixture
def mock_admin_user():
    """Мок для администратора"""
    admin = MagicMock()
    admin.email = "admin@example.com"
    admin.is_admin = True
    admin.is_super_admin = False
    return admin

@pytest.fixture
def mock_super_admin_user():
    """Мок для суперадминистратора"""
    super_admin = MagicMock()
    super_admin.email = "superadmin@example.com"
    super_admin.is_admin = True
    super_admin.is_super_admin = True
    return super_admin

@pytest.fixture
def mock_user():
    """Мок для обычного пользователя"""
    user = MagicMock()
    user.id = 1
    user.email = "user@example.com"
    user.is_admin = False
    user.is_super_admin = False
    user.is_active = False
    return user

@pytest.fixture
def client():
    """Тестовый клиент FastAPI"""
    from fastapi import FastAPI
    app = FastAPI()
    app.include_router(router)
    return TestClient(app)

# Тесты для service-key middleware
@pytest.mark.asyncio
async def test_verify_service_key_valid():
    """Тест проверки валидного сервисного ключа"""
    # Патчим значение INTERNAL_SERVICE_KEY
    with patch('admin_router.INTERNAL_SERVICE_KEY', 'test'):
        result = await verify_service_key(service_key='test')
        assert result is True

@pytest.mark.asyncio
async def test_verify_service_key_invalid():
    """Тест проверки невалидного сервисного ключа"""
    with patch('admin_router.INTERNAL_SERVICE_KEY', 'test'):
        with pytest.raises(HTTPException) as exc_info:
            await verify_service_key(service_key='invalid')
        assert exc_info.value.status_code == 401
        assert "Отсутствует или неверный сервисный ключ" in exc_info.value.detail

@pytest.mark.asyncio
async def test_verify_service_key_missing():
    """Тест проверки отсутствующего сервисного ключа"""
    with patch('admin_router.INTERNAL_SERVICE_KEY', 'test'):
        with pytest.raises(HTTPException) as exc_info:
            await verify_service_key(service_key=None)
        assert exc_info.value.status_code == 401
        assert "Отсутствует или неверный сервисный ключ" in exc_info.value.detail

# Тесты для эндпоинтов admin_router
@pytest.mark.asyncio
async def test_get_all_users(mock_session, mock_admin_user):
    """Тест получения списка всех пользователей"""
    # Подготовка данных
    user1 = MagicMock()
    user1.id = 1
    user1.email = "user1@example.com"
    
    user2 = MagicMock()
    user2.id = 2
    user2.email = "user2@example.com"
    
    mock_users = [user1, user2]
    
    # Настройка поведения для sqlalchemy запроса
    execute_result = MagicMock()
    scalars_result = MagicMock()
    scalars_result.all.return_value = mock_users
    execute_result.scalars.return_value = scalars_result
    
    mock_session.execute = AsyncMock(return_value=execute_result)
    
    # Патчим select чтобы избежать ошибки при выполнении запроса
    with patch('admin_router.select', return_value="mocked_stmt"), \
         patch('admin_router.get_session', return_value=mock_session), \
         patch('admin_router.get_admin_user', return_value=mock_admin_user):
        from admin_router import get_all_users
        result = await get_all_users(session=mock_session)
    
    # Проверка результата
    assert result == mock_users
    mock_session.execute.assert_called_once_with("mocked_stmt")

@pytest.mark.asyncio
async def test_admin_activate_user(mock_session, mock_admin_user, mock_user):
    """Тест активации пользователя администратором"""
    # Подготовка данных
    user_id = 1
    
    # Патчим статический метод get_by_id
    with patch('models.UserModel.get_by_id', new_callable=AsyncMock) as mock_get_by_id:
        mock_get_by_id.return_value = mock_user
        
        # Вызов тестируемой функции
        with patch('admin_router.get_session', return_value=mock_session), \
             patch('admin_router.get_admin_user', return_value=mock_admin_user):
            from admin_router import admin_activate_user
            result = await admin_activate_user(user_id=user_id, session=mock_session)
        
        # Проверка результата
        assert result["message"] == f"Пользователь {mock_user.email} активирован"
        assert mock_user.is_active is True
        assert mock_user.activation_token is None
        mock_session.commit.assert_called_once()

@pytest.mark.asyncio
async def test_admin_activate_user_not_found(mock_session, mock_admin_user):
    """Тест активации несуществующего пользователя"""
    # Подготовка данных
    user_id = 999
    
    # Патчим статический метод get_by_id
    with patch('models.UserModel.get_by_id', new_callable=AsyncMock) as mock_get_by_id:
        mock_get_by_id.return_value = None
        
        # Вызов тестируемой функции
        with patch('admin_router.get_session', return_value=mock_session), \
             patch('admin_router.get_admin_user', return_value=mock_admin_user):
            from admin_router import admin_activate_user
            with pytest.raises(HTTPException) as exc_info:
                await admin_activate_user(user_id=user_id, session=mock_session)
        
        # Проверка результата
        assert exc_info.value.status_code == 404
        assert "Пользователь не найден" in exc_info.value.detail

@pytest.mark.asyncio
async def test_make_user_admin(mock_session, mock_super_admin_user, mock_user):
    """Тест назначения пользователя администратором"""
    # Подготовка данных
    user_id = 1
    
    # Патчим статический метод get_by_id
    with patch('models.UserModel.get_by_id', new_callable=AsyncMock) as mock_get_by_id:
        mock_get_by_id.return_value = mock_user
        
        # Вызов тестируемой функции
        with patch('admin_router.get_session', return_value=mock_session), \
             patch('admin_router.get_super_admin_user', return_value=mock_super_admin_user):
            from admin_router import make_user_admin
            result = await make_user_admin(user_id=user_id, session=mock_session)
        
        # Проверка результата
        assert result["message"] == f"Пользователю {mock_user.email} предоставлены права администратора"
        assert mock_user.is_admin is True
        mock_session.commit.assert_called_once()

@pytest.mark.asyncio
async def test_remove_admin_rights(mock_session, mock_super_admin_user, mock_user):
    """Тест отзыва прав администратора у пользователя"""
    # Подготовка данных
    user_id = 1
    mock_user.is_admin = True
    
    # Патчим статический метод get_by_id
    with patch('models.UserModel.get_by_id', new_callable=AsyncMock) as mock_get_by_id:
        mock_get_by_id.return_value = mock_user
        
        # Вызов тестируемой функции
        with patch('admin_router.get_session', return_value=mock_session), \
             patch('admin_router.get_super_admin_user', return_value=mock_super_admin_user):
            from admin_router import remove_admin_rights
            result = await remove_admin_rights(user_id=user_id, session=mock_session)
        
        # Проверка результата
        assert result["message"] == f"У пользователя {mock_user.email} отозваны права администратора"
        assert mock_user.is_admin is False
        mock_session.commit.assert_called_once()

@pytest.mark.asyncio
async def test_remove_admin_rights_super_admin(mock_session, mock_super_admin_user):
    """Тест отзыва прав администратора у суперадминистратора (запрещено)"""
    # Подготовка данных
    user_id = 1
    super_user = MagicMock()
    super_user.email = "super@example.com"
    super_user.is_admin = True
    super_user.is_super_admin = True
    
    # Патчим статический метод get_by_id
    with patch('models.UserModel.get_by_id', new_callable=AsyncMock) as mock_get_by_id:
        mock_get_by_id.return_value = super_user
        
        # Вызов тестируемой функции
        with patch('admin_router.get_session', return_value=mock_session), \
             patch('admin_router.get_super_admin_user', return_value=mock_super_admin_user):
            from admin_router import remove_admin_rights
            with pytest.raises(HTTPException) as exc_info:
                await remove_admin_rights(user_id=user_id, session=mock_session)
        
        # Проверка результата
        assert exc_info.value.status_code == 400
        assert "Невозможно отозвать права администратора у суперадминистратора" in exc_info.value.detail

@pytest.mark.asyncio
async def test_delete_user(mock_session, mock_super_admin_user, mock_user):
    """Тест удаления пользователя"""
    # Подготовка данных
    user_id = 1
    
    # Патчим статический метод get_by_id
    with patch('models.UserModel.get_by_id', new_callable=AsyncMock) as mock_get_by_id:
        mock_get_by_id.return_value = mock_user
        
        # Вызов тестируемой функции
        with patch('admin_router.get_session', return_value=mock_session), \
             patch('admin_router.get_super_admin_user', return_value=mock_super_admin_user):
            from admin_router import delete_user
            result = await delete_user(user_id=user_id, session=mock_session)
        
        # Проверка результата
        assert result["message"] == f"Пользователь {mock_user.email} удален"
        mock_session.delete.assert_called_once_with(mock_user)
        mock_session.commit.assert_called_once()

@pytest.mark.asyncio
async def test_check_admin_access(mock_admin_user):
    """Тест проверки прав администратора"""
    # Вызов тестируемой функции
    with patch('admin_router.get_admin_user', return_value=mock_admin_user):
        from admin_router import check_admin_access
        result = await check_admin_access()
    
    # Проверка результата
    assert result["status"] == "success"
    assert result["message"] == "У вас есть права администратора"

@pytest.mark.asyncio
async def test_check_super_admin_access(mock_super_admin_user):
    """Тест проверки прав суперадминистратора"""
    # Вызов тестируемой функции
    with patch('admin_router.get_super_admin_user', return_value=mock_super_admin_user):
        from admin_router import check_super_admin_access
        result = await check_super_admin_access()
    
    # Проверка результата
    assert result["status"] == "success"
    assert result["message"] == "У вас есть права суперадминистратора"

@pytest.mark.asyncio
async def test_get_user_by_id(mock_session, mock_user):
    """Тест получения пользователя по ID (межсервисный запрос)"""
    # Подготовка данных
    user_id = 1
    
    # Патчим статический метод get_by_id
    with patch('models.UserModel.get_by_id', new_callable=AsyncMock) as mock_get_by_id:
        mock_get_by_id.return_value = mock_user
        
        # Вызов тестируемой функции
        with patch('admin_router.get_session', return_value=mock_session), \
             patch('admin_router.verify_service_jwt', return_value=True):
            from admin_router import get_user_by_id
            result = await get_user_by_id(user_id=user_id, session=mock_session)
        
        # Проверка результата
        assert result == mock_user

@pytest.mark.asyncio
async def test_get_user_by_id_not_found(mock_session):
    """Тест получения несуществующего пользователя по ID"""
    # Подготовка данных
    user_id = 999
    
    # Патчим статический метод get_by_id
    with patch('models.UserModel.get_by_id', new_callable=AsyncMock) as mock_get_by_id:
        mock_get_by_id.return_value = None
        
        # Вызов тестируемой функции
        with patch('admin_router.get_session', return_value=mock_session), \
             patch('admin_router.verify_service_jwt', return_value=True):
            from admin_router import get_user_by_id
            with pytest.raises(HTTPException) as exc_info:
                await get_user_by_id(user_id=user_id, session=mock_session)
        
        # Проверка результата
        assert exc_info.value.status_code == 404
        assert "Пользователь не найден" in exc_info.value.detail 