"""Дополнительные тесты для административных функций из admin_router.py."""

import pytest
from unittest.mock import AsyncMock, patch
from fastapi import HTTPException

from admin_router import (
    make_user_admin, remove_admin_rights, delete_user, get_user_by_id
)

@pytest.mark.asyncio
async def test_make_user_admin_not_found(mock_session):
    """Тест предоставления прав администратора несуществующему пользователю."""
    # Данные для тестирования
    user_id = 999  # ID несуществующего пользователя
    
    # Патчим UserModel.get_by_id для имитации отсутствия пользователя
    with patch('admin_router.UserModel.get_by_id', new_callable=AsyncMock) as mock_get_by_id:
        # Настраиваем мок - пользователь не найден
        mock_get_by_id.return_value = None
        
        # Проверяем, что функция вызывает исключение
        with pytest.raises(HTTPException) as exc_info:
            await make_user_admin(user_id=user_id, session=mock_session)
        
        # Проверяем исключение
        assert exc_info.value.status_code == 404
        assert "Пользователь не найден" in exc_info.value.detail
        
        # Проверяем, что get_by_id был вызван с правильными параметрами
        mock_get_by_id.assert_called_once_with(mock_session, user_id)

@pytest.mark.asyncio
async def test_remove_admin_rights_not_found(mock_session):
    """Тест отзыва прав администратора у несуществующего пользователя."""
    # Данные для тестирования
    user_id = 999  # ID несуществующего пользователя
    
    # Патчим UserModel.get_by_id для имитации отсутствия пользователя
    with patch('admin_router.UserModel.get_by_id', new_callable=AsyncMock) as mock_get_by_id:
        # Настраиваем мок - пользователь не найден
        mock_get_by_id.return_value = None
        
        # Проверяем, что функция вызывает исключение
        with pytest.raises(HTTPException) as exc_info:
            await remove_admin_rights(user_id=user_id, session=mock_session)
        
        # Проверяем исключение
        assert exc_info.value.status_code == 404
        assert "Пользователь не найден" in exc_info.value.detail
        
        # Проверяем, что get_by_id был вызван с правильными параметрами
        mock_get_by_id.assert_called_once_with(mock_session, user_id)

@pytest.mark.asyncio
async def test_delete_user_not_found(mock_session):
    """Тест удаления несуществующего пользователя."""
    # Данные для тестирования
    user_id = 999  # ID несуществующего пользователя
    
    # Патчим UserModel.get_by_id для имитации отсутствия пользователя
    with patch('admin_router.UserModel.get_by_id', new_callable=AsyncMock) as mock_get_by_id:
        # Настраиваем мок - пользователь не найден
        mock_get_by_id.return_value = None
        
        # Проверяем, что функция вызывает исключение
        with pytest.raises(HTTPException) as exc_info:
            await delete_user(user_id=user_id, session=mock_session)
        
        # Проверяем исключение
        assert exc_info.value.status_code == 404
        assert "Пользователь не найден" in exc_info.value.detail
        
        # Проверяем, что get_by_id был вызван с правильными параметрами
        mock_get_by_id.assert_called_once_with(mock_session, user_id)

@pytest.mark.asyncio
async def test_get_user_by_id_not_found(mock_session):
    """Тест получения несуществующего пользователя по ID."""
    # Данные для тестирования
    user_id = 999  # ID несуществующего пользователя
    
    # Патчим UserModel.get_by_id и verify_service_jwt
    with patch('admin_router.UserModel.get_by_id', new_callable=AsyncMock) as mock_get_by_id, \
         patch('admin_router.verify_service_jwt', return_value=True):
        # Настраиваем мок - пользователь не найден
        mock_get_by_id.return_value = None
        
        # Проверяем, что функция вызывает исключение
        with pytest.raises(HTTPException) as exc_info:
            await get_user_by_id(user_id=user_id, session=mock_session)
        
        # Проверяем исключение
        assert exc_info.value.status_code == 404
        assert "Пользователь не найден" in exc_info.value.detail
        
        # Проверяем, что get_by_id был вызван с правильными параметрами
        mock_get_by_id.assert_called_once_with(mock_session, user_id) 