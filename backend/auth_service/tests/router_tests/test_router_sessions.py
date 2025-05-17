"""Тесты для управления сессиями пользователей."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import HTTPException, status

from router import (
    get_user_sessions, revoke_user_session, revoke_all_user_sessions
)

@pytest.mark.asyncio
async def test_get_user_sessions(mock_session, mock_user):
    """Тест получения списка сессий пользователя"""
    # Мок для сессий пользователя
    session1 = MagicMock()
    session1.id = 1
    session1.jti = "jti1"
    session1.user_agent = "Chrome"
    session1.ip_address = "127.0.0.1"
    session1.created_at = MagicMock()
    session1.expires_at = MagicMock()
    session1.is_active = True
    
    session2 = MagicMock()
    session2.id = 2
    session2.jti = "jti2"
    session2.user_agent = "Firefox"
    session2.ip_address = "127.0.0.1"
    session2.created_at = MagicMock()
    session2.expires_at = MagicMock()
    session2.is_active = True
    
    # Патчим сервисную функцию
    with patch('router.session_service.get_user_sessions', new_callable=AsyncMock) as mock_get_sessions:
        # Настраиваем поведение мока
        mock_get_sessions.return_value = [session1, session2]
        
        # Вызываем тестируемую функцию
        result = await get_user_sessions(session=mock_session, current_user=mock_user)
        
        # Проверяем результат
        assert len(result["sessions"]) == 2
        assert result["sessions"][0]["id"] == 1
        assert result["sessions"][0]["jti"] == "jti1"
        assert result["sessions"][0]["user_agent"] == "Chrome"
        assert result["sessions"][1]["id"] == 2
        assert result["sessions"][1]["jti"] == "jti2"
        assert result["sessions"][1]["user_agent"] == "Firefox"
        
        # Проверяем вызов функции
        mock_get_sessions.assert_called_once_with(mock_session, mock_user.id)

@pytest.mark.asyncio
async def test_get_user_sessions_error(mock_session, mock_user):
    """Тест обработки ошибки при получении списка сессий"""
    # Патчим сервисную функцию
    with patch('router.session_service.get_user_sessions', new_callable=AsyncMock) as mock_get_sessions:
        # Настраиваем, чтобы функция вызывала исключение
        mock_get_sessions.side_effect = Exception("Database error")
        
        # Проверяем, что функция вызывает HTTPException
        with pytest.raises(HTTPException) as exc_info:
            await get_user_sessions(session=mock_session, current_user=mock_user)
        
        # Проверяем исключение
        assert exc_info.value.status_code == 500
        assert "Ошибка при получении информации о сессиях" in exc_info.value.detail
        
        # Проверяем вызов функции
        mock_get_sessions.assert_called_once_with(mock_session, mock_user.id)

@pytest.mark.asyncio
async def test_revoke_user_session_success(mock_session, mock_user):
    """Тест успешного отзыва сессии пользователя"""
    # Данные для тестирования
    session_id = 1
    
    # Патчим сервисную функцию
    with patch('router.session_service.revoke_session', new_callable=AsyncMock) as mock_revoke:
        # Настраиваем поведение мока
        mock_revoke.return_value = True  # Сессия успешно отозвана
        
        # Вызываем тестируемую функцию
        result = await revoke_user_session(
            session_id=session_id,
            session=mock_session,
            current_user=mock_user
        )
        
        # Проверяем результат
        assert result["status"] == "success"
        assert "Сессия успешно отозвана" in result["message"]
        
        # Проверяем вызов функции
        mock_revoke.assert_called_once_with(
            session=mock_session,
            session_id=session_id,
            user_id=mock_user.id
        )

@pytest.mark.asyncio
async def test_revoke_user_session_not_found(mock_session, mock_user):
    """Тест отзыва несуществующей сессии пользователя"""
    # Данные для тестирования
    session_id = 999
    
    # Патчим сервисную функцию
    with patch('router.session_service.revoke_session', new_callable=AsyncMock) as mock_revoke:
        # Настраиваем поведение мока - сессия не найдена
        mock_revoke.return_value = False
        
        # Проверяем, что функция вызывает HTTPException
        with pytest.raises(HTTPException) as exc_info:
            await revoke_user_session(
                session_id=session_id,
                session=mock_session,
                current_user=mock_user
            )
        
        # Проверяем исключение
        assert exc_info.value.status_code == 404
        assert "Сессия не найдена или не принадлежит пользователю" in exc_info.value.detail
        
        # Проверяем вызов функции
        mock_revoke.assert_called_once_with(
            session=mock_session,
            session_id=session_id,
            user_id=mock_user.id
        )

@pytest.mark.asyncio
async def test_revoke_all_user_sessions_success(mock_session, mock_user):
    """Тест успешного отзыва всех сессий пользователя"""
    # Данные для тестирования
    token = "test_token"
    
    # Патчим сервисные функции
    with patch('router.TokenService.decode_token', new_callable=AsyncMock) as mock_decode, \
         patch('router.session_service.revoke_all_user_sessions', new_callable=AsyncMock) as mock_revoke_all:
        
        # Настраиваем поведение моков
        mock_decode.return_value = {"jti": "current_jti"}
        mock_revoke_all.return_value = 3  # Количество отозванных сессий
        
        # Вызываем тестируемую функцию
        result = await revoke_all_user_sessions(
            session=mock_session,
            current_user=mock_user,
            token=token,
            authorization=None
        )
        
        # Проверяем результат
        assert result["status"] == "success"
        assert "Отозвано 3 сессий" in result["message"]
        assert result["revoked_count"] == 3
        
        # Проверяем вызовы функций
        mock_decode.assert_called_once_with(token)
        mock_revoke_all.assert_called_once_with(
            session=mock_session,
            user_id=mock_user.id,
            exclude_jti="current_jti"
        )

@pytest.mark.asyncio
async def test_revoke_all_user_sessions_no_token(mock_session, mock_user):
    """Тест отзыва всех сессий без текущего токена"""
    # Данные для тестирования - нет токена
    token = None
    authorization = None
    
    # Патчим сервисную функцию
    with patch('router.session_service.revoke_all_user_sessions', new_callable=AsyncMock) as mock_revoke_all:
        # Настраиваем поведение мока
        mock_revoke_all.return_value = 5  # Количество отозванных сессий
        
        # Вызываем тестируемую функцию
        result = await revoke_all_user_sessions(
            session=mock_session,
            current_user=mock_user,
            token=token,
            authorization=authorization
        )
        
        # Проверяем результат
        assert result["status"] == "success"
        assert "Отозвано 5 сессий" in result["message"]
        assert result["revoked_count"] == 5
        
        # Проверяем вызов функции - отзываем все сессии (без исключений)
        mock_revoke_all.assert_called_once_with(
            session=mock_session,
            user_id=mock_user.id,
            exclude_jti=None
        )

@pytest.mark.asyncio
async def test_revoke_all_user_sessions_with_auth_header(mock_session, mock_user):
    """Тест отзыва всех сессий с токеном в заголовке авторизации"""
    # Данные для тестирования
    token = None
    authorization = "Bearer test_token_from_header"
    
    # Патчим сервисные функции
    with patch('router.TokenService.decode_token', new_callable=AsyncMock) as mock_decode, \
         patch('router.session_service.revoke_all_user_sessions', new_callable=AsyncMock) as mock_revoke_all:
        
        # Настраиваем поведение моков
        mock_decode.return_value = {"jti": "header_jti"}
        mock_revoke_all.return_value = 2  # Количество отозванных сессий
        
        # Вызываем тестируемую функцию
        result = await revoke_all_user_sessions(
            session=mock_session,
            current_user=mock_user,
            token=token,
            authorization=authorization
        )
        
        # Проверяем результат
        assert result["status"] == "success"
        assert "Отозвано 2 сессий" in result["message"]
        assert result["revoked_count"] == 2
        
        # Проверяем вызовы функций
        mock_decode.assert_called_once_with("test_token_from_header")
        mock_revoke_all.assert_called_once_with(
            session=mock_session,
            user_id=mock_user.id,
            exclude_jti="header_jti"
        ) 