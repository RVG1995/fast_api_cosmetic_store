"""Тесты для модуля кэширования (cache_service.py)."""

import json
import pickle
import hashlib
import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch

# Импортируем тестируемый модуль
from app.services.auth.cache_service import CacheService, cache_service, cached
from config import settings

# Константы для тестов
TEST_KEY = "test_key"
TEST_VALUE = {"name": "test", "value": 42}
TEST_COMPLEX_VALUE = {"data": [1, 2, 3], "nested": {"key": "value"}}
TEST_TTL = 300

# Тесты для конструктора CacheService
def test_service_constructor_cache_disabled():
    """Тест конструктора CacheService при отключенном кэшировании."""
    # Патчим константу CACHE_ENABLED в модуле cache_service
    with patch('app.services.auth.cache_service.CACHE_ENABLED', False):
        # Создаем экземпляр сервиса
        service = CacheService()
        
        # Проверяем, что кэширование отключено
        assert service.enabled is False
        assert service.redis is None
        
        # Проверяем, что initialize не пытается подключиться к Redis
        with patch('redis.asyncio.Redis.from_url') as mock_from_url:
            # Вызываем initialize (асинхронно)
            import asyncio
            asyncio.run(service.initialize())
            
            # Проверяем, что метод from_url не вызывался
            mock_from_url.assert_not_called()

@pytest_asyncio.fixture
async def mock_redis():
    """Заглушка для Redis клиента."""
    mock = AsyncMock()
    
    # Настраиваем методы Redis клиента
    mock.get = AsyncMock()
    mock.setex = AsyncMock()
    mock.delete = AsyncMock()
    mock.scan = AsyncMock()
    mock.close = AsyncMock()
    mock.from_url = AsyncMock()
    
    return mock

@pytest_asyncio.fixture
async def cache_service_instance(mock_redis):
    """Экземпляр сервиса кэширования с замоканным Redis."""
    service = CacheService()
    service.redis = mock_redis
    service.enabled = True
    return service

# Тесты для инициализации сервиса
@pytest.mark.asyncio
async def test_initialize_success():
    """Тест успешной инициализации сервиса."""
    # Создаем экземпляр сервиса
    service = CacheService()
    service.enabled = True
    
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
        assert kwargs["decode_responses"] is False

@pytest.mark.asyncio
async def test_initialize_with_cache_disabled():
    """Тест инициализации сервиса с отключенным кэшированием."""
    # Создаем экземпляр сервиса с отключенным кэшированием
    service = CacheService()
    service.enabled = False
    
    # Вызываем метод initialize
    await service.initialize()
    
    # Проверяем, что Redis подключение не создавалось
    assert service.redis is None
    assert service.enabled is False

@pytest.mark.asyncio
async def test_initialize_with_password():
    """Тест инициализации сервиса с паролем Redis."""
    # Создаем экземпляр сервиса
    service = CacheService()
    service.enabled = True
    
    # Патчим настройки и метод from_url для Redis
    with patch('app.services.auth.cache_service.REDIS_PASSWORD', "redis_password"), \
         patch('redis.asyncio.Redis.from_url', new_callable=AsyncMock) as mock_from_url:
        
        # Настраиваем мок для имитации успешного подключения
        mock_redis = AsyncMock()
        mock_from_url.return_value = mock_redis
        
        # Вызываем метод initialize
        await service.initialize()
        
        # Проверяем, что подключение создано
        assert service.redis is not None
        assert service.enabled is True
        
        # Проверяем, что from_url был вызван с правильной строкой подключения
        mock_from_url.assert_called_once()
        args, _ = mock_from_url.call_args
        assert ":redis_password@" in args[0]  # Проверяем, что URL содержит пароль

@pytest.mark.asyncio
async def test_initialize_redis_error():
    """Тест инициализации сервиса при ошибке подключения к Redis."""
    # Создаем экземпляр сервиса
    service = CacheService()
    service.enabled = True
    
    # Подменяем метод from_url для Redis, чтобы он вызывал исключение
    with patch('redis.asyncio.Redis.from_url', new_callable=AsyncMock) as mock_from_url:
        # Имитируем ошибку подключения
        import redis.asyncio as redis
        mock_from_url.side_effect = redis.ConnectionError("Connection refused")
        
        # Вызываем метод initialize
        await service.initialize()
        
        # Проверяем, что сервис правильно обработал ошибку
        assert service.redis is None
        assert service.enabled is False

# Тесты для метода get
@pytest.mark.asyncio
async def test_get_cache_hit_pickle(cache_service_instance):
    """Тест получения данных из кэша, сериализованных с помощью pickle."""
    # Подготавливаем тестовые данные
    pickled_data = pickle.dumps(TEST_VALUE)
    
    # Настраиваем мок Redis.get для возврата сериализованных данных
    cache_service_instance.redis.get.return_value = pickled_data
    
    # Вызываем метод get и проверяем результат
    result = await cache_service_instance.get(TEST_KEY)
    
    # Проверяем, что метод вернул ожидаемое значение
    assert result == TEST_VALUE
    
    # Проверяем, что Redis.get был вызван с правильным ключом
    cache_service_instance.redis.get.assert_called_once_with(TEST_KEY)

@pytest.mark.asyncio
async def test_get_cache_hit_json(cache_service_instance):
    """Тест получения данных из кэша, сериализованных как JSON."""
    # Подготавливаем тестовые данные
    json_data = json.dumps(TEST_VALUE).encode('utf-8')
    
    # Настраиваем мок Redis.get для возврата данных
    # Также настраиваем, чтобы pickle.loads вызывал исключение
    cache_service_instance.redis.get.return_value = json_data
    
    # Тестируем, что данные корректно десериализуются из JSON если pickle не сработал
    with patch('pickle.loads', side_effect=pickle.UnpicklingError):
        result = await cache_service_instance.get(TEST_KEY)
    
    # Проверяем, что метод вернул ожидаемое значение
    assert result == TEST_VALUE
    
    # Проверяем, что Redis.get был вызван с правильным ключом
    cache_service_instance.redis.get.assert_called_once_with(TEST_KEY)

@pytest.mark.asyncio
async def test_get_cache_hit_raw_bytes(cache_service_instance):
    """Тест получения сырых байтов из кэша."""
    # Подготавливаем тестовые данные
    raw_data = b"raw binary data"
    
    # Настраиваем мок Redis.get для возврата данных
    cache_service_instance.redis.get.return_value = raw_data
    
    # Тестируем, что сырые данные возвращаются, если pickle и JSON не сработали
    with patch('pickle.loads', side_effect=pickle.UnpicklingError), \
         patch('json.loads', side_effect=json.JSONDecodeError("", "", 0)):
        result = await cache_service_instance.get(TEST_KEY)
    
    # Проверяем, что метод вернул ожидаемое значение
    assert result == raw_data
    
    # Проверяем, что Redis.get был вызван с правильным ключом
    cache_service_instance.redis.get.assert_called_once_with(TEST_KEY)

@pytest.mark.asyncio
async def test_get_cache_miss(cache_service_instance):
    """Тест получения данных из кэша, когда ключ не найден."""
    # Настраиваем мок Redis.get для возврата None (ключ не найден)
    cache_service_instance.redis.get.return_value = None
    
    # Вызываем метод get и проверяем результат
    result = await cache_service_instance.get(TEST_KEY)
    
    # Проверяем, что метод вернул None
    assert result is None
    
    # Проверяем, что Redis.get был вызван с правильным ключом
    cache_service_instance.redis.get.assert_called_once_with(TEST_KEY)

@pytest.mark.asyncio
async def test_get_redis_error(cache_service_instance):
    """Тест получения данных из кэша при ошибке Redis."""
    # Настраиваем мок Redis.get для имитации ошибки
    import redis.asyncio as redis
    cache_service_instance.redis.get.side_effect = redis.RedisError("Connection refused")
    
    # Вызываем метод get и проверяем результат
    result = await cache_service_instance.get(TEST_KEY)
    
    # Проверяем, что метод вернул None при ошибке
    assert result is None
    
    # Проверяем, что Redis.get был вызван с правильным ключом
    cache_service_instance.redis.get.assert_called_once_with(TEST_KEY)

@pytest.mark.asyncio
async def test_get_cache_disabled(cache_service_instance):
    """Тест получения данных из кэша, когда кэширование отключено."""
    # Отключаем Redis
    cache_service_instance.enabled = False
    
    # Вызываем метод get и проверяем результат
    result = await cache_service_instance.get(TEST_KEY)
    
    # Проверяем, что метод вернул None
    assert result is None
    
    # Проверяем, что Redis.get не вызывался
    cache_service_instance.redis.get.assert_not_called()

# Тесты для метода set
@pytest.mark.asyncio
async def test_set_success(cache_service_instance):
    """Тест успешного сохранения данных в кэш."""
    # Настраиваем мок Redis.setex для успешного сохранения
    cache_service_instance.redis.setex.return_value = True
    
    # Вызываем метод set и проверяем результат
    result = await cache_service_instance.set(TEST_KEY, TEST_VALUE, TEST_TTL)
    
    # Проверяем, что метод вернул True (успешное сохранение)
    assert result is True
    
    # Проверяем, что Redis.setex был вызван с правильными параметрами
    cache_service_instance.redis.setex.assert_called_once()
    args, _ = cache_service_instance.redis.setex.call_args
    assert args[0] == TEST_KEY
    assert args[1] == TEST_TTL
    # Третий аргумент - сериализованные данные

@pytest.mark.asyncio
async def test_set_redis_error(cache_service_instance):
    """Тест сохранения данных в кэш при ошибке Redis."""
    # Настраиваем мок Redis.setex для имитации ошибки
    import redis.asyncio as redis
    cache_service_instance.redis.setex.side_effect = redis.RedisError("Connection refused")
    
    # Вызываем метод set и проверяем результат
    result = await cache_service_instance.set(TEST_KEY, TEST_VALUE, TEST_TTL)
    
    # Проверяем, что метод вернул False при ошибке
    assert result is False
    
    # Проверяем, что Redis.setex был вызван
    cache_service_instance.redis.setex.assert_called_once()

@pytest.mark.asyncio
async def test_set_cache_disabled(cache_service_instance):
    """Тест сохранения данных в кэш, когда кэширование отключено."""
    # Отключаем Redis
    cache_service_instance.enabled = False
    
    # Вызываем метод set и проверяем результат
    result = await cache_service_instance.set(TEST_KEY, TEST_VALUE, TEST_TTL)
    
    # Проверяем, что метод вернул False
    assert result is False
    
    # Проверяем, что Redis.setex не вызывался
    cache_service_instance.redis.setex.assert_not_called()

# Тесты для метода delete
@pytest.mark.asyncio
async def test_delete_success(cache_service_instance):
    """Тест успешного удаления ключа из кэша."""
    # Настраиваем мок Redis.delete для успешного удаления
    cache_service_instance.redis.delete.return_value = 1
    
    # Вызываем метод delete и проверяем результат
    result = await cache_service_instance.delete(TEST_KEY)
    
    # Проверяем, что метод вернул True (успешное удаление)
    assert result is True
    
    # Проверяем, что Redis.delete был вызван с правильным ключом
    cache_service_instance.redis.delete.assert_called_once_with(TEST_KEY)

@pytest.mark.asyncio
async def test_delete_redis_error(cache_service_instance):
    """Тест удаления ключа из кэша при ошибке Redis."""
    # Настраиваем мок Redis.delete для имитации ошибки
    import redis.asyncio as redis
    cache_service_instance.redis.delete.side_effect = redis.RedisError("Connection refused")
    
    # Вызываем метод delete и проверяем результат
    result = await cache_service_instance.delete(TEST_KEY)
    
    # Проверяем, что метод вернул False при ошибке
    assert result is False
    
    # Проверяем, что Redis.delete был вызван с правильным ключом
    cache_service_instance.redis.delete.assert_called_once_with(TEST_KEY)

@pytest.mark.asyncio
async def test_delete_cache_disabled(cache_service_instance):
    """Тест удаления ключа из кэша, когда кэширование отключено."""
    # Отключаем Redis
    cache_service_instance.enabled = False
    
    # Вызываем метод delete и проверяем результат
    result = await cache_service_instance.delete(TEST_KEY)
    
    # Проверяем, что метод вернул False
    assert result is False
    
    # Проверяем, что Redis.delete не вызывался
    cache_service_instance.redis.delete.assert_not_called()

# Тесты для метода delete_pattern
@pytest.mark.asyncio
async def test_delete_pattern_success(cache_service_instance):
    """Тест успешного удаления ключей по шаблону."""
    # Настраиваем мок Redis.scan для имитации нахождения ключей
    cache_service_instance.redis.scan.side_effect = [
        (1, ["key1", "key2"]),  # Первый вызов scan возвращает cursor=1 и два ключа
        (0, ["key3"])           # Второй вызов возвращает cursor=0 (конец) и один ключ
    ]
    
    # Настраиваем мок Redis.delete для успешного удаления
    cache_service_instance.redis.delete.return_value = 3  # Удалено 3 ключа
    
    # Вызываем метод delete_pattern и проверяем результат
    result = await cache_service_instance.delete_pattern("test_*")
    
    # Проверяем, что метод вернул количество удаленных ключей
    assert result == 3
    
    # Проверяем, что Redis.scan был вызван дважды с правильными параметрами
    assert cache_service_instance.redis.scan.call_count == 2
    
    # Проверяем, что Redis.delete был вызван с правильными ключами
    cache_service_instance.redis.delete.assert_called_once_with("key1", "key2", "key3")

@pytest.mark.asyncio
async def test_delete_pattern_no_keys(cache_service_instance):
    """Тест удаления ключей по шаблону, когда ключи не найдены."""
    # Настраиваем мок Redis.scan для имитации отсутствия ключей
    cache_service_instance.redis.scan.return_value = (0, [])  # Нет ключей
    
    # Вызываем метод delete_pattern и проверяем результат
    result = await cache_service_instance.delete_pattern("test_*")
    
    # Проверяем, что метод вернул 0 (нет удаленных ключей)
    assert result == 0
    
    # Проверяем, что Redis.scan был вызван с правильными параметрами
    cache_service_instance.redis.scan.assert_called_once()
    
    # Проверяем, что Redis.delete не вызывался
    cache_service_instance.redis.delete.assert_not_called()

@pytest.mark.asyncio
async def test_delete_pattern_redis_error(cache_service_instance):
    """Тест удаления ключей по шаблону при ошибке Redis."""
    # Настраиваем мок Redis.scan для имитации ошибки
    import redis.asyncio as redis
    cache_service_instance.redis.scan.side_effect = redis.RedisError("Connection refused")
    
    # Вызываем метод delete_pattern и проверяем результат
    result = await cache_service_instance.delete_pattern("test_*")
    
    # Проверяем, что метод вернул 0 при ошибке
    assert result == 0
    
    # Проверяем, что Redis.scan был вызван
    cache_service_instance.redis.scan.assert_called_once()
    
    # Проверяем, что Redis.delete не вызывался
    cache_service_instance.redis.delete.assert_not_called()

@pytest.mark.asyncio
async def test_delete_pattern_cache_disabled(cache_service_instance):
    """Тест удаления ключей по шаблону, когда кэширование отключено."""
    # Отключаем Redis
    cache_service_instance.enabled = False
    
    # Вызываем метод delete_pattern и проверяем результат
    result = await cache_service_instance.delete_pattern("test_*")
    
    # Проверяем, что метод вернул 0
    assert result == 0
    
    # Проверяем, что Redis.scan не вызывался
    cache_service_instance.redis.scan.assert_not_called()
    
    # Проверяем, что Redis.delete не вызывался
    cache_service_instance.redis.delete.assert_not_called()

# Тесты для метода get_key_for_user
def test_get_key_for_user(cache_service_instance):
    """Тест формирования ключа кэша для пользователя."""
    # Тестовые данные
    user_id = 123
    action = "profile"
    
    # Вызываем метод и проверяем результат
    result = cache_service_instance.get_key_for_user(user_id, action)
    
    # Проверяем формат ключа
    assert result == f"user:{user_id}:{action}"
    
    # Тест со строковым user_id
    user_id = "user123"
    result = cache_service_instance.get_key_for_user(user_id, action)
    assert result == f"user:{user_id}:{action}"

# Тесты для метода get_key_for_function
def test_get_key_for_function_simple(cache_service_instance):
    """Тест формирования простого ключа кэша для функции."""
    # Тестовые данные
    prefix = "my_function"
    arg1 = "value1"
    arg2 = 42
    
    # Вызываем метод и проверяем результат
    result = cache_service_instance.get_key_for_function(prefix, arg1, arg2)
    
    # Проверяем формат ключа
    assert result == f"{prefix}:{arg1}:{arg2}"

def test_get_key_for_function_with_kwargs(cache_service_instance):
    """Тест формирования ключа кэша для функции с именованными аргументами."""
    # Тестовые данные
    prefix = "my_function"
    
    # Вызываем метод и проверяем результат
    result = cache_service_instance.get_key_for_function(prefix, id=123, name="test")
    
    # Проверяем формат ключа (с именованными аргументами в алфавитном порядке)
    assert result == f"{prefix}:id:123:name:test"

def test_get_key_for_function_long_key(cache_service_instance):
    """Тест формирования хешированного ключа, если он слишком длинный."""
    # Тестовые данные
    prefix = "my_function"
    long_arg = "x" * 200  # Очень длинный аргумент
    
    # Вызываем метод и проверяем результат
    result = cache_service_instance.get_key_for_function(prefix, long_arg)
    
    # Проверяем, что ключ был хеширован
    expected_key_str = f"{prefix}:{long_arg}"
    expected_hash = hashlib.md5(expected_key_str.encode()).hexdigest()
    assert result == f"{prefix}:hash:{expected_hash}"

# Тесты для метода close
@pytest.mark.asyncio
async def test_close_connection(cache_service_instance):
    """Тест закрытия соединения с Redis."""
    # Вызываем метод close
    await cache_service_instance.close()
    
    # Проверяем, что Redis.close был вызван
    cache_service_instance.redis.close.assert_called_once()

@pytest.mark.asyncio
async def test_close_connection_no_redis(cache_service_instance):
    """Тест закрытия соединения, когда Redis не инициализирован."""
    # Устанавливаем redis в None
    cache_service_instance.redis = None
    
    # Вызываем метод close (не должно быть исключений)
    await cache_service_instance.close()

# Тесты для декоратора cached
@pytest.mark.asyncio
async def test_cached_decorator_cache_hit(monkeypatch):
    """Тест декоратора cached при наличии данных в кэше."""
    # Создаем мок для get
    mock_get = AsyncMock()
    # Настраиваем мок для возврата кэшированного результата
    cached_result = {"arg1": "value1", "arg2": "value2"}
    mock_get.return_value = cached_result
    
    # Создаем мок для get_key_for_function
    mock_key_builder = MagicMock()
    mock_key_builder.return_value = "test_function:value1:arg2:value2"
    
    # Применяем патчи
    monkeypatch.setattr(cache_service, 'get', mock_get)
    monkeypatch.setattr(cache_service, 'get_key_for_function', mock_key_builder)
    monkeypatch.setattr(cache_service, 'enabled', True)
    monkeypatch.setattr(cache_service, 'redis', AsyncMock())
    
    # Создаем тестовую функцию и декорируем ее
    @cached()
    async def test_function(arg1, arg2=None):
        return {"arg1": arg1, "arg2": arg2}
    
    # Вызываем декорированную функцию
    result = await test_function("value1", arg2="value2")
    
    # Проверяем, что был возвращен кэшированный результат
    assert result == cached_result
    
    # Проверяем, что метод get был вызван с правильным ключом
    mock_get.assert_called_once_with("test_function:value1:arg2:value2")
    
    # Проверяем, что get_key_for_function был вызван с правильными параметрами
    mock_key_builder.assert_called_once()

@pytest.mark.asyncio
async def test_cached_decorator_cache_miss(monkeypatch):
    """Тест декоратора cached при отсутствии данных в кэше."""
    # Создаем мок для get
    mock_get = AsyncMock()
    mock_get.return_value = None  # Нет данных в кэше
    
    # Создаем мок для set
    mock_set = AsyncMock()
    mock_set.return_value = True
    
    # Создаем мок для get_key_for_function
    mock_key_builder = MagicMock()
    mock_key_builder.return_value = "test_function:value1:arg2:value2"
    
    # Применяем патчи
    monkeypatch.setattr(cache_service, 'get', mock_get)
    monkeypatch.setattr(cache_service, 'set', mock_set)
    monkeypatch.setattr(cache_service, 'get_key_for_function', mock_key_builder)
    monkeypatch.setattr(cache_service, 'enabled', True)
    monkeypatch.setattr(cache_service, 'redis', AsyncMock())
    
    # Ожидаемый результат выполнения функции
    expected_result = {"arg1": "value1", "arg2": "value2"}
    
    # Создаем тестовую функцию и декорируем ее
    @cached(ttl=TEST_TTL)
    async def test_function(arg1, arg2=None):
        return {"arg1": arg1, "arg2": arg2}
    
    # Вызываем декорированную функцию
    result = await test_function("value1", arg2="value2")
    
    # Проверяем, что функция вернула ожидаемый результат
    assert result == expected_result
    
    # Проверяем, что метод get был вызван с правильным ключом
    mock_get.assert_called_once_with("test_function:value1:arg2:value2")
    
    # Проверяем, что метод set был вызван для сохранения результата в кэш
    # Проверяем отдельно каждый аргумент, так как порядок может быть важен
    assert mock_set.call_count == 1
    args, kwargs = mock_set.call_args
    assert args[0] == "test_function:value1:arg2:value2"
    assert args[1] == expected_result
    assert kwargs.get('ttl') == TEST_TTL or args[2] == TEST_TTL

@pytest.mark.asyncio
async def test_cached_decorator_with_custom_key_builder(monkeypatch):
    """Тест декоратора cached с пользовательским построителем ключа."""
    # Создаем мок для get
    mock_get = AsyncMock()
    mock_get.return_value = None  # Нет данных в кэше
    
    # Создаем мок для set
    mock_set = AsyncMock()
    mock_set.return_value = True
    
    # Применяем патчи
    monkeypatch.setattr(cache_service, 'get', mock_get)
    monkeypatch.setattr(cache_service, 'set', mock_set)
    monkeypatch.setattr(cache_service, 'enabled', True)
    monkeypatch.setattr(cache_service, 'redis', AsyncMock())
    
    # Пользовательский построитель ключа
    def custom_key_builder(arg1, arg2=None):
        return f"custom_key:{arg1}:{arg2}"
    
    # Ожидаемый ключ
    expected_key = "custom_key:value1:value2"
    
    # Создаем тестовую функцию и декорируем ее
    @cached(key_builder=custom_key_builder)
    async def test_function(arg1, arg2=None):
        return {"arg1": arg1, "arg2": arg2}
    
    # Вызываем декорированную функцию
    await test_function("value1", arg2="value2")
    
    # Проверяем, что метод get был вызван с правильным пользовательским ключом
    mock_get.assert_called_once_with(expected_key)

@pytest.mark.asyncio
async def test_cached_decorator_cache_disabled():
    """Тест декоратора cached при отключенном кэшировании."""
    # Создаем тестовую асинхронную функцию
    @cached()
    async def test_function(arg1, arg2=None):
        return {"arg1": arg1, "arg2": arg2}
    
    # Ожидаемый результат выполнения функции
    expected_result = {"arg1": "value1", "arg2": "value2"}
    
    # Временно отключаем кэширование
    original_enabled = cache_service.enabled
    cache_service.enabled = False
    
    try:
        # Патчим методы get и set для проверки, что они не вызываются
        with patch.object(cache_service, 'get', new_callable=AsyncMock) as mock_get, \
             patch.object(cache_service, 'set', new_callable=AsyncMock) as mock_set:
            
            # Вызываем декорированную функцию
            result = await test_function("value1", arg2="value2")
            
            # Проверяем, что функция вернула ожидаемый результат
            assert result == expected_result
            
            # Проверяем, что методы get и set не вызывались
            mock_get.assert_not_called()
            mock_set.assert_not_called()
    finally:
        # Восстанавливаем исходное состояние
        cache_service.enabled = original_enabled

        cache_service.enabled = original_enabled 