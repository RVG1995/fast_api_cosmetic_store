"""Тесты для функции verify_service_jwt из utils.py."""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi import HTTPException

from utils import verify_service_jwt


@pytest.mark.asyncio
async def test_verify_service_jwt_valid():
    """Тест проверки валидного JWT с правильным scope"""
    # Создаем мок для HTTPAuthorizationCredentials
    mock_cred = MagicMock()
    mock_cred.credentials = "valid_token"
    
    # Создаем мок для jwt.decode
    mock_payload = {"scope": "service"}
    
    with patch("jwt.decode", return_value=mock_payload):
        # Вызываем функцию и проверяем результат
        result = await verify_service_jwt(cred=mock_cred)
        assert result is True


@pytest.mark.asyncio
async def test_verify_service_jwt_invalid_scope():
    """Тест проверки JWT с неверным scope"""
    # Создаем мок для HTTPAuthorizationCredentials
    mock_cred = MagicMock()
    mock_cred.credentials = "valid_token_wrong_scope"
    
    # Создаем мок для jwt.decode с неверным scope
    mock_payload = {"scope": "user"}
    
    with patch("jwt.decode", return_value=mock_payload):
        # Проверяем, что функция вызывает исключение
        with pytest.raises(HTTPException) as exc_info:
            await verify_service_jwt(cred=mock_cred)
        
        # Проверяем статус код и сообщение об ошибке
        assert exc_info.value.status_code == 403
        assert "Insufficient scope" in exc_info.value.detail


@pytest.mark.asyncio
async def test_verify_service_jwt_missing_token():
    """Тест проверки отсутствующего JWT"""
    # Создаем мок для HTTPAuthorizationCredentials без токена
    mock_cred = None
    
    # Проверяем, что функция вызывает исключение
    with pytest.raises(HTTPException) as exc_info:
        await verify_service_jwt(cred=mock_cred)
    
    # Проверяем статус код и сообщение об ошибке
    assert exc_info.value.status_code == 401
    assert "Missing bearer token" in exc_info.value.detail


@pytest.mark.asyncio
async def test_verify_service_jwt_empty_token():
    """Тест проверки пустого JWT"""
    # Создаем мок для HTTPAuthorizationCredentials с пустым токеном
    mock_cred = MagicMock()
    mock_cred.credentials = None
    
    # Проверяем, что функция вызывает исключение
    with pytest.raises(HTTPException) as exc_info:
        await verify_service_jwt(cred=mock_cred)
    
    # Проверяем статус код и сообщение об ошибке
    assert exc_info.value.status_code == 401
    assert "Missing bearer token" in exc_info.value.detail


@pytest.mark.asyncio
async def test_verify_service_jwt_invalid_token():
    """Тест проверки недействительного JWT"""
    # Создаем мок для HTTPAuthorizationCredentials
    mock_cred = MagicMock()
    mock_cred.credentials = "invalid_token"
    
    # Патчим jwt.decode чтобы он вызывал исключение
    with patch("jwt.decode", side_effect=Exception("Invalid token")):
        # Проверяем, что функция вызывает исключение
        with pytest.raises(HTTPException) as exc_info:
            await verify_service_jwt(cred=mock_cred)
        
        # Проверяем статус код и сообщение об ошибке
        assert exc_info.value.status_code == 401
        assert "Invalid token" in exc_info.value.detail 