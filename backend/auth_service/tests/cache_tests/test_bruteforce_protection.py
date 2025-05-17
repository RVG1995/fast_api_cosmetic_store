"""Тесты для модуля защиты от брутфорс-атак."""

import json
import time
import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch

# Импортируем тестируемый модуль
from app.services.auth.bruteforce_protection import BruteforceProtection, bruteforce_protection

# Константы для тестов
TEST_IP = "127.0.0.1"
TEST_USERNAME = "test@example.com"

# Фикстуры для тестирования Redis
@pytest_asyncio.fixture
async def mock_redis():
    """Заглушка для Redis клиента."""
    mock = AsyncMock()
    
    # Настраиваем методы Redis клиента
    mock.get = AsyncMock()
    mock.setex = AsyncMock()
    mock.delete = AsyncMock()
    mock.close = AsyncMock()
    
    return mock

@pytest_asyncio.fixture
async def protection_service(mock_redis):
    """Экземпляр сервиса защиты от брутфорса с замоканным Redis."""
    service = BruteforceProtection()
    service.redis = mock_redis
    service.enabled = True
    return service

# Тесты для инициализации сервиса
@pytest.mark.asyncio
async def test_initialize_success():
    """Тест успешной инициализации сервиса."""
    # Создаем экземпляр сервиса
    service = BruteforceProtection()
    
    # Подменяем метод from_url для Redis
    with patch('redis.asyncio.Redis.from_url', new_callable=AsyncMock) as mock_from_url:
        # Настраиваем мок для имитации успешного подключения
        mock_redis = AsyncMock()
        mock_from_url.return_value = mock_redis
        
        # Вызываем метод initialize
        await service.initialize()
        
        # Проверяем, что подключение создано
        assert service.redis is not None
        assert service.enabled is True
        
        # Проверяем, что from_url был вызван с правильными параметрами
        mock_from_url.assert_called_once()
        _, kwargs = mock_from_url.call_args
        assert kwargs["socket_timeout"] == 3
        assert kwargs["decode_responses"] is True

@pytest.mark.asyncio
async def test_initialize_failure():
    """Тест инициализации сервиса при ошибке подключения к Redis."""
    # Создаем экземпляр сервиса
    service = BruteforceProtection()
    
    # Подменяем метод from_url для Redis, чтобы он вызывал исключение
    with patch('redis.asyncio.Redis.from_url', new_callable=AsyncMock) as mock_from_url:
        # Настраиваем мок для имитации ошибки подключения
        import redis.asyncio as redis
        mock_from_url.side_effect = redis.ConnectionError("Connection refused")
        
        # Вызываем метод initialize
        await service.initialize()
        
        # Проверяем, что сервис правильно обработал ошибку
        assert service.redis is None
        assert service.enabled is False

@pytest.mark.asyncio
async def test_initialize_with_password():
    """Тест инициализации сервиса с паролем Redis."""
    # Создаем экземпляр сервиса
    service = BruteforceProtection()
    
    # Патчим настройки и подменяем метод from_url для Redis
    with patch('app.services.auth.bruteforce_protection.REDIS_PASSWORD', "redis_password"), \
         patch('redis.asyncio.Redis.from_url', new_callable=AsyncMock) as mock_from_url:
        
        # Настраиваем мок для имитации успешного подключения
        mock_redis = AsyncMock()
        mock_from_url.return_value = mock_redis
        
        # Вызываем метод initialize
        await service.initialize()
        
        # Проверяем, что подключение создано
        assert service.redis is not None
        assert service.enabled is True
        
        # Проверяем, что from_url был вызван с правильными параметрами и URL содержит пароль
        mock_from_url.assert_called_once()
        args, _ = mock_from_url.call_args
        assert ":redis_password@" in args[0]  # Проверяем, что URL содержит пароль

# Тесты для проверки блокировки IP
@pytest.mark.asyncio
async def test_check_ip_blocked_not_blocked(protection_service):
    """Тест проверки, что IP не заблокирован."""
    # Настраиваем мок Redis.get для возврата None (IP не заблокирован)
    protection_service.redis.get.return_value = None
    
    # Вызываем метод и проверяем результат
    result = await protection_service.check_ip_blocked(TEST_IP)
    
    # Проверяем, что метод вернул False (не заблокирован)
    assert result is False
    
    # Проверяем, что Redis.get был вызван с правильным ключом
    protection_service.redis.get.assert_called_once_with(f"ip_block:{TEST_IP}")
    
    # Проверяем, что Redis.delete не вызывался
    protection_service.redis.delete.assert_not_called()

@pytest.mark.asyncio
async def test_check_ip_blocked_still_blocked(protection_service):
    """Тест проверки, что IP заблокирован и время блокировки не истекло."""
    # Текущее время
    current_time = int(time.time())
    
    # Время блокировки до (текущее время + 300 секунд)
    blocked_until = current_time + 300
    
    # Настраиваем мок Redis.get для возврата времени блокировки
    protection_service.redis.get.return_value = str(blocked_until)
    
    # Вызываем метод и проверяем результат
    result = await protection_service.check_ip_blocked(TEST_IP)
    
    # Проверяем, что метод вернул True (заблокирован)
    assert result is True
    
    # Проверяем, что Redis.get был вызван с правильным ключом
    protection_service.redis.get.assert_called_once_with(f"ip_block:{TEST_IP}")
    
    # Проверяем, что Redis.delete не вызывался
    protection_service.redis.delete.assert_not_called()

@pytest.mark.asyncio
async def test_check_ip_blocked_expired(protection_service):
    """Тест проверки, что IP был заблокирован, но время блокировки истекло."""
    # Текущее время
    current_time = int(time.time())
    
    # Время блокировки до (текущее время - 10 секунд, т.е. уже истекло)
    blocked_until = current_time - 10
    
    # Настраиваем мок Redis.get для возврата истекшего времени блокировки
    protection_service.redis.get.return_value = str(blocked_until)
    
    # Вызываем метод и проверяем результат
    result = await protection_service.check_ip_blocked(TEST_IP)
    
    # Проверяем, что метод вернул False (не заблокирован, т.к. время истекло)
    assert result is False
    
    # Проверяем, что Redis.get был вызван с правильным ключом
    protection_service.redis.get.assert_called_once_with(f"ip_block:{TEST_IP}")
    
    # Проверяем, что Redis.delete был вызван для удаления истекшей блокировки
    protection_service.redis.delete.assert_called_once_with(f"ip_block:{TEST_IP}")

@pytest.mark.asyncio
async def test_check_ip_blocked_redis_error(protection_service):
    """Тест проверки блокировки IP при ошибке Redis."""
    # Настраиваем мок Redis.get для имитации ошибки подключения
    import redis.asyncio as redis
    protection_service.redis.get.side_effect = redis.ConnectionError("Connection refused")
    
    # Вызываем метод и проверяем результат
    result = await protection_service.check_ip_blocked(TEST_IP)
    
    # Проверяем, что метод вернул False (считаем не заблокированным при ошибке)
    assert result is False
    
    # Проверяем, что Redis.get был вызван с правильным ключом
    protection_service.redis.get.assert_called_once_with(f"ip_block:{TEST_IP}")

@pytest.mark.asyncio
async def test_check_ip_blocked_redis_disabled(protection_service):
    """Тест проверки блокировки IP когда Redis отключен."""
    # Отключаем Redis
    protection_service.enabled = False
    
    # Вызываем метод и проверяем результат
    result = await protection_service.check_ip_blocked(TEST_IP)
    
    # Проверяем, что метод вернул False (считаем не заблокированным при отключенном Redis)
    assert result is False
    
    # Проверяем, что Redis.get не вызывался
    protection_service.redis.get.assert_not_called()

# Тесты для регистрации неудачных попыток входа
@pytest.mark.asyncio
async def test_record_failed_attempt_first(protection_service):
    """Тест регистрации первой неудачной попытки входа."""
    # Настраиваем мок Redis.get для возврата None (первая попытка)
    protection_service.redis.get.return_value = None
    
    # Вызываем метод и проверяем результат
    result = await protection_service.record_failed_attempt(TEST_IP, TEST_USERNAME)
    
    # Проверяем, что метод вернул ожидаемый результат
    assert result["blocked"] is False
    assert result["attempts"] == 1
    assert result["remaining_attempts"] == 4  # MAX_FAILED_ATTEMPTS - 1
    
    # Проверяем, что Redis.get был вызван с правильным ключом
    expected_key = f"login_attempts:{TEST_IP}:{TEST_USERNAME}"
    protection_service.redis.get.assert_called_once_with(expected_key)
    
    # Проверяем, что Redis.setex был вызван с правильными параметрами
    protection_service.redis.setex.assert_called_once()
    args, _ = protection_service.redis.setex.call_args
    assert args[0] == expected_key  # Ключ
    assert args[1] == 3600  # TTL (ATTEMPT_TTL)
    # В значении должен быть count=1
    data = json.loads(args[2])
    assert data["count"] == 1
    assert "last_attempt" in data

@pytest.mark.asyncio
async def test_record_failed_attempt_increment(protection_service):
    """Тест увеличения счетчика неудачных попыток входа."""
    # Настраиваем мок Redis.get для возврата данных о предыдущих попытках
    previous_attempts = json.dumps({"count": 2, "last_attempt": int(time.time()) - 60})
    protection_service.redis.get.return_value = previous_attempts
    
    # Вызываем метод и проверяем результат
    result = await protection_service.record_failed_attempt(TEST_IP, TEST_USERNAME)
    
    # Проверяем, что метод вернул ожидаемый результат
    assert result["blocked"] is False
    assert result["attempts"] == 3  # 2 + 1
    assert result["remaining_attempts"] == 2  # MAX_FAILED_ATTEMPTS - 3
    
    # Проверяем, что Redis.setex был вызван с правильными параметрами
    protection_service.redis.setex.assert_called_once()
    args, _ = protection_service.redis.setex.call_args
    data = json.loads(args[2])
    assert data["count"] == 3

@pytest.mark.asyncio
async def test_record_failed_attempt_invalid_json(protection_service):
    """Тест обработки невалидного JSON при получении счетчика попыток."""
    # Настраиваем мок Redis.get для возврата невалидного JSON
    protection_service.redis.get.return_value = "not-a-json"
    
    # Вызываем метод и проверяем результат
    result = await protection_service.record_failed_attempt(TEST_IP, TEST_USERNAME)
    
    # Проверяем, что метод корректно обработал ошибку и вернул результат с 1 попыткой
    assert result["blocked"] is False
    assert result["attempts"] == 1  # Сбрасывает счетчик при ошибке
    assert result["remaining_attempts"] == 4  # MAX_FAILED_ATTEMPTS - 1
    
    # Проверяем, что Redis.setex был вызван с правильными параметрами
    protection_service.redis.setex.assert_called_once()
    args, _ = protection_service.redis.setex.call_args
    data = json.loads(args[2])
    assert data["count"] == 1

@pytest.mark.asyncio
async def test_record_failed_attempt_block_ip(protection_service):
    """Тест блокировки IP после достижения лимита неудачных попыток."""
    # Настраиваем мок Redis.get для возврата данных о предыдущих попытках (4 попытки)
    previous_attempts = json.dumps({"count": 4, "last_attempt": int(time.time()) - 60})
    protection_service.redis.get.return_value = previous_attempts
    
    # Вызываем метод и проверяем результат
    result = await protection_service.record_failed_attempt(TEST_IP, TEST_USERNAME)
    
    # Проверяем, что метод вернул ожидаемый результат
    assert result["blocked"] is True
    assert result["attempts"] == 5  # 4 + 1 = 5, что равно MAX_FAILED_ATTEMPTS
    assert result["remaining_attempts"] == 0
    assert "blocked_until" in result
    assert "blocked_for" in result
    assert result["blocked_for"] == 300  # BLOCK_TIME
    
    # Проверяем, что Redis.setex был вызван дважды:
    # 1. Для обновления счетчика попыток
    # 2. Для создания блокировки IP
    assert protection_service.redis.setex.call_count == 2
    
    # Проверяем вызов для блокировки IP
    block_key = f"ip_block:{TEST_IP}"
    # Находим вызов с ключом блокировки
    block_call = next((call for call in protection_service.redis.setex.call_args_list if call[0][0] == block_key), None)
    assert block_call is not None
    assert block_call[0][1] == 300  # BLOCK_TIME
    
    # Проверяем, что Redis.delete был вызван для сброса счетчика попыток
    expected_key = f"login_attempts:{TEST_IP}:{TEST_USERNAME}"
    protection_service.redis.delete.assert_called_once_with(expected_key)

@pytest.mark.asyncio
async def test_record_failed_attempt_ip_only(protection_service):
    """Тест регистрации неудачной попытки входа только по IP (без имени пользователя)."""
    # Настраиваем мок Redis.get для возврата None (первая попытка)
    protection_service.redis.get.return_value = None
    
    # Вызываем метод и проверяем результат (без указания имени пользователя)
    result = await protection_service.record_failed_attempt(TEST_IP)
    
    # Проверяем, что метод вернул ожидаемый результат
    assert result["blocked"] is False
    assert result["attempts"] == 1
    assert result["remaining_attempts"] == 4  # MAX_FAILED_ATTEMPTS - 1
    
    # Проверяем, что Redis.get был вызван с правильным ключом (только IP)
    expected_key = f"login_attempts:{TEST_IP}"
    protection_service.redis.get.assert_called_once_with(expected_key)
    
    # Проверяем, что Redis.setex был вызван с правильными параметрами
    protection_service.redis.setex.assert_called_once()
    args, _ = protection_service.redis.setex.call_args
    assert args[0] == expected_key  # Ключ

@pytest.mark.asyncio
async def test_record_failed_attempt_redis_disabled(protection_service):
    """Тест регистрации неудачной попытки входа при отключенном Redis."""
    # Отключаем Redis
    protection_service.enabled = False
    
    # Вызываем метод и проверяем результат
    result = await protection_service.record_failed_attempt(TEST_IP, TEST_USERNAME)
    
    # Проверяем, что метод вернул значения по умолчанию
    assert result["blocked"] is False
    assert result["attempts"] == 0
    assert result["remaining_attempts"] == 5  # MAX_FAILED_ATTEMPTS
    
    # Проверяем, что Redis.get не вызывался
    protection_service.redis.get.assert_not_called()
    protection_service.redis.setex.assert_not_called()

# Тесты для сброса счетчика попыток
@pytest.mark.asyncio
async def test_reset_attempts_with_username(protection_service):
    """Тест сброса счетчика попыток для IP и пользователя."""
    # Вызываем метод и проверяем результат
    result = await protection_service.reset_attempts(TEST_IP, TEST_USERNAME)
    
    # Проверяем, что метод вернул True (успешный сброс)
    assert result is True
    
    # Проверяем, что Redis.delete был вызван дважды:
    # 1. Для ключа с IP и пользователем
    # 2. Для ключа только с IP
    assert protection_service.redis.delete.call_count == 2
    
    # Проверяем, что ключи правильные
    delete_calls = [call[0][0] for call in protection_service.redis.delete.call_args_list]
    assert f"login_attempts:{TEST_IP}:{TEST_USERNAME}" in delete_calls
    assert f"login_attempts:{TEST_IP}" in delete_calls

@pytest.mark.asyncio
async def test_reset_attempts_ip_only(protection_service):
    """Тест сброса счетчика попыток только для IP."""
    # Вызываем метод без указания пользователя
    result = await protection_service.reset_attempts(TEST_IP)
    
    # Проверяем, что метод вернул True (успешный сброс)
    assert result is True
    
    # Проверяем, что Redis.delete был вызван один раз для ключа только с IP
    protection_service.redis.delete.assert_called_once_with(f"login_attempts:{TEST_IP}")

@pytest.mark.asyncio
async def test_reset_attempts_redis_disabled(protection_service):
    """Тест сброса счетчика попыток при отключенном Redis."""
    # Отключаем Redis
    protection_service.enabled = False
    
    # Вызываем метод и проверяем результат
    result = await protection_service.reset_attempts(TEST_IP, TEST_USERNAME)
    
    # Проверяем, что метод вернул False
    assert result is False
    
    # Проверяем, что Redis.delete не вызывался
    protection_service.redis.delete.assert_not_called()

@pytest.mark.asyncio
async def test_close_connection(protection_service):
    """Тест закрытия соединения с Redis."""
    # Вызываем метод close
    await protection_service.close()
    
    # Проверяем, что Redis.close был вызван
    protection_service.redis.close.assert_called_once()

# Тесты для обработки ошибок Redis
@pytest.mark.asyncio
async def test_record_failed_attempt_redis_error(protection_service):
    """Тест обработки ошибки Redis при регистрации неудачной попытки."""
    # Настраиваем мок Redis.get для имитации ошибки
    import redis.asyncio as redis
    protection_service.redis.get.side_effect = redis.ConnectionError("Connection refused")
    
    # Вызываем метод и проверяем результат
    result = await protection_service.record_failed_attempt(TEST_IP, TEST_USERNAME)
    
    # Проверяем, что метод вернул значения по умолчанию
    assert result["blocked"] is False
    assert result["attempts"] == 0
    assert result["remaining_attempts"] == 5  # MAX_FAILED_ATTEMPTS

@pytest.mark.asyncio
async def test_reset_attempts_redis_error(protection_service):
    """Тест обработки ошибки Redis при сбросе счетчика попыток."""
    # Настраиваем мок Redis.delete для имитации ошибки
    import redis.asyncio as redis
    protection_service.redis.delete.side_effect = redis.ConnectionError("Connection refused")
    
    # Вызываем метод и проверяем результат
    result = await protection_service.reset_attempts(TEST_IP, TEST_USERNAME)
    
    # Проверяем, что метод вернул False (ошибка сброса)
    assert result is False 