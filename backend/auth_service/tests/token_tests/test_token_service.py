"""Тесты для модуля управления JWT токенами (token_service.py)."""

import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch
import jwt
from datetime import datetime, timezone, timedelta
import uuid

# Импортируем тестируемый модуль
from app.services.auth.token_service import TokenService

# Константы для тестов
TEST_SECRET_KEY = "test_secret_key"
TEST_ALGORITHM = "HS256"
TEST_DATA = {"sub": "test_user", "is_admin": False}
TEST_JTI = "test-jti-123"

# Фикстуры для тестирования
@pytest_asyncio.fixture
async def token_service_instance():
    """Экземпляр сервиса токенов для тестирования."""
    return TokenService()

# Патч для конфигурации
@pytest.fixture
def mock_config():
    """Мок для конфигурации JWT."""
    with patch('app.services.auth.token_service.SECRET_KEY', TEST_SECRET_KEY), \
         patch('app.services.auth.token_service.ALGORITHM', TEST_ALGORITHM):
        yield

# Тесты для create_access_token
@pytest.mark.asyncio
async def test_create_access_token_success(mock_config):
    """Тест успешного создания JWT токена."""
    # Патчим uuid.uuid4 для предсказуемого JTI
    with patch('uuid.uuid4', return_value=TEST_JTI):
        # Создаем тестовые данные
        expires_delta = timedelta(minutes=30)
        
        # Вызываем тестируемый метод
        token, jti = await TokenService.create_access_token(
            data=TEST_DATA,
            expires_delta=expires_delta
        )
        
        # Проверяем тип результата
        assert isinstance(token, str)
        assert jti == TEST_JTI
        
        # Декодируем токен для проверки
        payload = jwt.decode(token, TEST_SECRET_KEY, algorithms=[TEST_ALGORITHM])
        
        # Проверяем основные поля
        assert payload["sub"] == TEST_DATA["sub"]
        assert payload["is_admin"] == TEST_DATA["is_admin"]
        assert payload["jti"] == TEST_JTI
        assert "exp" in payload
        assert "iat" in payload
        assert "nbf" in payload

@pytest.mark.asyncio
async def test_create_access_token_default_expiry(mock_config):
    """Тест создания JWT токена с использованием срока действия по умолчанию."""
    # Патчим get_access_token_expires_delta для предсказуемого значения
    default_expires = timedelta(minutes=15)
    with patch('app.services.auth.token_service.get_access_token_expires_delta', return_value=default_expires), \
         patch('uuid.uuid4', return_value=TEST_JTI):
        
        # Вызываем тестируемый метод без указания expires_delta
        token, jti = await TokenService.create_access_token(data=TEST_DATA)
        
        # Декодируем токен для проверки
        payload = jwt.decode(token, TEST_SECRET_KEY, algorithms=[TEST_ALGORITHM])
        
        # Проверяем, что срок действия установлен
        assert "exp" in payload
        
        # Проверяем, что jti корректный
        assert jti == TEST_JTI
        assert payload["jti"] == TEST_JTI

# Тесты для decode_token
@pytest.mark.asyncio
async def test_decode_token_success(mock_config):
    """Тест успешного декодирования JWT токена."""
    # Создаем тестовый токен
    expires = datetime.now(timezone.utc) + timedelta(minutes=30)
    payload = {
        "sub": "test_user",
        "exp": expires.timestamp(),
        "iat": datetime.now(timezone.utc).timestamp(),
        "jti": TEST_JTI
    }
    token = jwt.encode(payload, TEST_SECRET_KEY, algorithm=TEST_ALGORITHM)
    
    # Вызываем тестируемый метод
    result = await TokenService.decode_token(token)
    
    # Проверяем результат
    assert result["sub"] == payload["sub"]
    assert result["jti"] == payload["jti"]

@pytest.mark.asyncio
async def test_decode_token_expired(mock_config):
    """Тест декодирования истекшего JWT токена."""
    # Создаем истекший токен
    expires = datetime.now(timezone.utc) - timedelta(minutes=30)
    payload = {
        "sub": "test_user",
        "exp": expires.timestamp(),
        "iat": (expires - timedelta(minutes=30)).timestamp(),
        "jti": TEST_JTI
    }
    token = jwt.encode(payload, TEST_SECRET_KEY, algorithm=TEST_ALGORITHM)
    
    # Вызываем тестируемый метод и ожидаем исключение
    with pytest.raises(jwt.ExpiredSignatureError):
        await TokenService.decode_token(token)

@pytest.mark.asyncio
async def test_decode_token_invalid(mock_config):
    """Тест декодирования недействительного JWT токена."""
    # Создаем недействительный токен
    token = "invalid.token.string"
    
    # Вызываем тестируемый метод и ожидаем исключение
    with pytest.raises(jwt.InvalidTokenError):
        await TokenService.decode_token(token)

# Тесты для get_token_expiry
@pytest.mark.asyncio
async def test_get_token_expiry_success(mock_config):
    """Тест успешного получения времени истечения JWT токена."""
    # Создаем тестовый токен с заданным временем истечения
    exp_time = datetime.now(timezone.utc) + timedelta(minutes=30)
    exp_timestamp = exp_time.timestamp()
    payload = {
        "sub": "test_user",
        "exp": exp_timestamp,
        "iat": datetime.now(timezone.utc).timestamp(),
        "jti": TEST_JTI
    }
    token = jwt.encode(payload, TEST_SECRET_KEY, algorithm=TEST_ALGORITHM)
    
    # Вызываем тестируемый метод
    result = await TokenService.get_token_expiry(token)
    
    # Проверяем результат (сравниваем по временным меткам из-за возможных расхождений в микросекундах)
    assert isinstance(result, datetime)
    assert result.timestamp() == pytest.approx(exp_timestamp, abs=1)

@pytest.mark.asyncio
async def test_get_token_expiry_no_exp(mock_config):
    """Тест получения времени истечения JWT токена без поля exp."""
    # Создаем токен без поля exp
    payload = {
        "sub": "test_user",
        "iat": datetime.now(timezone.utc).timestamp(),
        "jti": TEST_JTI
    }
    token = jwt.encode(payload, TEST_SECRET_KEY, algorithm=TEST_ALGORITHM)
    
    # Вызываем тестируемый метод
    result = await TokenService.get_token_expiry(token)
    
    # Проверяем, что результат None
    assert result is None

@pytest.mark.asyncio
async def test_get_token_expiry_invalid_token(mock_config):
    """Тест получения времени истечения недействительного JWT токена."""
    # Создаем недействительный токен
    token = "invalid.token.string"
    
    # Вызываем тестируемый метод
    result = await TokenService.get_token_expiry(token)
    
    # Проверяем, что результат None
    assert result is None

# Тесты для create_service_token
@pytest.mark.asyncio
async def test_create_service_token_success(mock_config):
    """Тест успешного создания сервисного JWT токена."""
    # Патчим получение срока действия сервисного токена
    service_expires = timedelta(minutes=15)
    with patch('app.services.auth.token_service.get_service_token_expires_delta', return_value=service_expires):
        # Вызываем тестируемый метод
        token = await TokenService.create_service_token("test_service")
        
        # Проверяем тип результата
        assert isinstance(token, str)
        
        # Декодируем токен для проверки
        payload = jwt.decode(token, TEST_SECRET_KEY, algorithms=[TEST_ALGORITHM])
        
        # Проверяем поля сервисного токена
        assert payload["sub"] == "test_service"
        assert payload["scope"] == "service"

@pytest.mark.asyncio
async def test_create_service_token_default_service(mock_config):
    """Тест создания сервисного JWT токена с использованием имени сервиса по умолчанию."""
    # Патчим получение срока действия сервисного токена
    service_expires = timedelta(minutes=15)
    with patch('app.services.auth.token_service.get_service_token_expires_delta', return_value=service_expires):
        # Вызываем тестируемый метод без указания имени сервиса
        token = await TokenService.create_service_token()
        
        # Декодируем токен для проверки
        payload = jwt.decode(token, TEST_SECRET_KEY, algorithms=[TEST_ALGORITHM])
        
        # Проверяем, что подставлено имя сервиса по умолчанию
        assert payload["sub"] == "auth_service"
        assert payload["scope"] == "service" 