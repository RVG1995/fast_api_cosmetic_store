"""Тесты для модуля auth_utils."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi import HTTPException, Cookie
import sys
import os

# Добавляем пути импорта для тестирования
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from auth_utils import get_current_user, get_admin_user, get_super_admin_user


@pytest.mark.asyncio
async def test_get_current_user_from_cookie(mock_session, mock_user):
    """Тест получения пользователя из cookie."""
    # Мокаем TokenService.decode_token
    token_payload = {"sub": str(mock_user.id), "jti": "test-session-id"}
    
    with patch("auth_utils.TokenService.decode_token", new_callable=AsyncMock) as mock_decode_token, \
         patch("auth_utils.session_service.is_session_active", new_callable=AsyncMock) as mock_is_session_active, \
         patch("auth_utils.user_service.get_user_by_id", new_callable=AsyncMock) as mock_get_user:
        
        mock_decode_token.return_value = token_payload
        mock_is_session_active.return_value = True
        mock_get_user.return_value = mock_user
        
        # Вызываем функцию с токеном в cookie
        result = await get_current_user(mock_session, token="test-token", authorization=None)
        
        # Проверяем результат
        assert result == mock_user
        mock_decode_token.assert_called_once_with("test-token")
        mock_is_session_active.assert_called_once_with(mock_session, "test-session-id")
        mock_get_user.assert_called_once_with(mock_session, mock_user.id)


@pytest.mark.asyncio
async def test_get_current_user_from_authorization_bearer(mock_session, mock_user):
    """Тест получения пользователя из заголовка Authorization с Bearer."""
    # Мокаем TokenService.decode_token
    token_payload = {"sub": str(mock_user.id), "jti": "test-session-id"}
    
    with patch("auth_utils.TokenService.decode_token", new_callable=AsyncMock) as mock_decode_token, \
         patch("auth_utils.session_service.is_session_active", new_callable=AsyncMock) as mock_is_session_active, \
         patch("auth_utils.user_service.get_user_by_id", new_callable=AsyncMock) as mock_get_user:
        
        mock_decode_token.return_value = token_payload
        mock_is_session_active.return_value = True
        mock_get_user.return_value = mock_user
        
        # Вызываем функцию с токеном в заголовке Authorization с префиксом Bearer
        result = await get_current_user(mock_session, token=None, authorization="Bearer test-token")
        
        # Проверяем результат
        assert result == mock_user
        mock_decode_token.assert_called_once_with("test-token")
        mock_is_session_active.assert_called_once_with(mock_session, "test-session-id")
        mock_get_user.assert_called_once_with(mock_session, mock_user.id)


@pytest.mark.asyncio
async def test_get_current_user_from_authorization_without_bearer(mock_session, mock_user):
    """Тест получения пользователя из заголовка Authorization без Bearer."""
    # Мокаем TokenService.decode_token
    token_payload = {"sub": str(mock_user.id), "jti": "test-session-id"}
    
    with patch("auth_utils.TokenService.decode_token", new_callable=AsyncMock) as mock_decode_token, \
         patch("auth_utils.session_service.is_session_active", new_callable=AsyncMock) as mock_is_session_active, \
         patch("auth_utils.user_service.get_user_by_id", new_callable=AsyncMock) as mock_get_user:
        
        mock_decode_token.return_value = token_payload
        mock_is_session_active.return_value = True
        mock_get_user.return_value = mock_user
        
        # Вызываем функцию с токеном в заголовке Authorization без префикса Bearer
        result = await get_current_user(mock_session, token=None, authorization="test-token")
        
        # Проверяем результат
        assert result == mock_user
        mock_decode_token.assert_called_once_with("test-token")
        mock_is_session_active.assert_called_once_with(mock_session, "test-session-id")
        mock_get_user.assert_called_once_with(mock_session, mock_user.id)


@pytest.mark.asyncio
async def test_get_current_user_no_token(mock_session):
    """Тест ошибки при отсутствии токена."""
    with pytest.raises(HTTPException) as exc_info:
        await get_current_user(mock_session, token=None, authorization=None)
    
    assert exc_info.value.status_code == 401
    assert "Токен не найден" in exc_info.value.detail


@pytest.mark.asyncio
async def test_get_current_user_invalid_token(mock_session):
    """Тест ошибки при невалидном токене."""
    with patch("auth_utils.TokenService.decode_token", new_callable=AsyncMock) as mock_decode_token:
        mock_decode_token.side_effect = Exception("Invalid token")
        
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(mock_session, token="invalid-token", authorization=None)
        
        assert exc_info.value.status_code == 401
        assert "Невозможно проверить учетные данные" in exc_info.value.detail


@pytest.mark.asyncio
async def test_get_current_user_missing_sub(mock_session):
    """Тест ошибки при отсутствии поля sub в токене."""
    with patch("auth_utils.TokenService.decode_token", new_callable=AsyncMock) as mock_decode_token:
        mock_decode_token.return_value = {"jti": "test-session-id"}  # Нет поля sub
        
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(mock_session, token="test-token", authorization=None)
        
        assert exc_info.value.status_code == 401
        assert "Невозможно проверить учетные данные" in exc_info.value.detail


@pytest.mark.asyncio
async def test_get_current_user_inactive_session(mock_session, mock_user):
    """Тест ошибки при неактивной сессии."""
    token_payload = {"sub": str(mock_user.id), "jti": "test-session-id"}
    
    with patch("auth_utils.TokenService.decode_token", new_callable=AsyncMock) as mock_decode_token, \
         patch("auth_utils.session_service.is_session_active", new_callable=AsyncMock) as mock_is_session_active:
        
        mock_decode_token.return_value = token_payload
        mock_is_session_active.return_value = False  # Сессия неактивна
        
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(mock_session, token="test-token", authorization=None)
        
        assert exc_info.value.status_code == 401
        assert "Токен был отозван" in exc_info.value.detail


@pytest.mark.asyncio
async def test_get_current_user_not_found(mock_session):
    """Тест ошибки при ненайденном пользователе."""
    token_payload = {"sub": "999", "jti": "test-session-id"}
    
    with patch("auth_utils.TokenService.decode_token", new_callable=AsyncMock) as mock_decode_token, \
         patch("auth_utils.session_service.is_session_active", new_callable=AsyncMock) as mock_is_session_active, \
         patch("auth_utils.user_service.get_user_by_id", new_callable=AsyncMock) as mock_get_user:
        
        mock_decode_token.return_value = token_payload
        mock_is_session_active.return_value = True
        mock_get_user.return_value = None  # Пользователь не найден
        
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(mock_session, token="test-token", authorization=None)
        
        assert exc_info.value.status_code == 401
        assert "Невозможно проверить учетные данные" in exc_info.value.detail


@pytest.mark.asyncio
async def test_get_current_user_inactive_user(mock_session, mock_user):
    """Тест ошибки при неактивном пользователе."""
    token_payload = {"sub": str(mock_user.id), "jti": "test-session-id"}
    inactive_user = MagicMock()
    inactive_user.id = mock_user.id
    inactive_user.is_active = False
    
    with patch("auth_utils.TokenService.decode_token", new_callable=AsyncMock) as mock_decode_token, \
         patch("auth_utils.session_service.is_session_active", new_callable=AsyncMock) as mock_is_session_active, \
         patch("auth_utils.user_service.get_user_by_id", new_callable=AsyncMock) as mock_get_user:
        
        mock_decode_token.return_value = token_payload
        mock_is_session_active.return_value = True
        mock_get_user.return_value = inactive_user
        
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(mock_session, token="test-token", authorization=None)
        
        assert exc_info.value.status_code == 401
        assert "Аккаунт не активирован" in exc_info.value.detail


@pytest.mark.asyncio
async def test_get_admin_user_success(mock_admin_user):
    """Тест успешной проверки прав администратора."""
    result = await get_admin_user(current_user=mock_admin_user)
    assert result == mock_admin_user


@pytest.mark.asyncio
async def test_get_admin_user_super_admin_access(mock_super_admin_user):
    """Тест успешной проверки прав для суперадминистратора."""
    result = await get_admin_user(current_user=mock_super_admin_user)
    assert result == mock_super_admin_user


@pytest.mark.asyncio
async def test_get_admin_user_forbidden(mock_user):
    """Тест запрета доступа для обычного пользователя."""
    with pytest.raises(HTTPException) as exc_info:
        await get_admin_user(current_user=mock_user)
    
    assert exc_info.value.status_code == 403
    assert "Недостаточно прав доступа" in exc_info.value.detail


@pytest.mark.asyncio
async def test_get_super_admin_user_success(mock_super_admin_user):
    """Тест успешной проверки прав суперадминистратора."""
    result = await get_super_admin_user(current_user=mock_super_admin_user)
    assert result == mock_super_admin_user


@pytest.mark.asyncio
async def test_get_super_admin_user_forbidden_admin(mock_admin_user):
    """Тест запрета доступа для обычного администратора."""
    with pytest.raises(HTTPException) as exc_info:
        await get_super_admin_user(current_user=mock_admin_user)
    
    assert exc_info.value.status_code == 403
    assert "Недостаточно прав доступа" in exc_info.value.detail


@pytest.mark.asyncio
async def test_get_super_admin_user_forbidden_user(mock_user):
    """Тест запрета доступа для обычного пользователя."""
    with pytest.raises(HTTPException) as exc_info:
        await get_super_admin_user(current_user=mock_user)
    
    assert exc_info.value.status_code == 403
    assert "Недостаточно прав доступа" in exc_info.value.detail 