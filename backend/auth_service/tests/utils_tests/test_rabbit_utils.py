"""Тесты для модуля утилит работы с RabbitMQ."""

import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch, Mock
import aio_pika
from aio_pika.exceptions import ChannelClosed

# Константы для тестов, соответствующие реальным значениям из кода
TEST_RABBITMQ_HOST = "localhost"
TEST_RABBITMQ_USER = "user"
TEST_RABBITMQ_PASS = "password"
TEST_DLX_NAME = "dead_letter_exchange"

# Мок для настроек
@pytest.fixture
def mock_settings():
    """Мок настроек RabbitMQ."""
    settings_mock = Mock()
    settings_mock.RABBITMQ_HOST = TEST_RABBITMQ_HOST
    settings_mock.RABBITMQ_USER = TEST_RABBITMQ_USER
    settings_mock.RABBITMQ_PASS = TEST_RABBITMQ_PASS
    settings_mock.DLX_NAME = TEST_DLX_NAME
    settings_mock.DLX_QUEUE = "dlx_queue"
    settings_mock.RETRY_DELAY_MS = 5000
    return settings_mock

# Патчим импорт настроек
@pytest.fixture
def patch_settings(mock_settings):
    """Патч для settings из модуля config."""
    with patch('app.utils.rabbit_utils.settings', mock_settings):
        yield mock_settings

# Тесты для модуля rabbit_utils
@pytest.mark.asyncio
async def test_get_connection(patch_settings):
    """Тест создания соединения с RabbitMQ."""
    # Патчим aio_pika.connect_robust
    with patch('aio_pika.connect_robust', new_callable=AsyncMock) as mock_connect:
        # Импортируем тестируемую функцию
        from app.utils.rabbit_utils import get_connection
        
        # Настраиваем мок
        connection_mock = AsyncMock()
        mock_connect.return_value = connection_mock
        
        # Вызываем тестируемую функцию
        result = await get_connection()
        
        # Проверяем, что функция вернула соединение
        assert result == connection_mock
        
        # Проверяем, что функция connect_robust была вызвана с правильными параметрами
        mock_connect.assert_called_once_with(
            host=TEST_RABBITMQ_HOST,
            login=TEST_RABBITMQ_USER,
            password=TEST_RABBITMQ_PASS
        )

@pytest.mark.asyncio
async def test_get_connection_error(patch_settings):
    """Тест обработки ошибки при создании соединения с RabbitMQ."""
    # Патчим aio_pika.connect_robust
    with patch('aio_pika.connect_robust', new_callable=AsyncMock) as mock_connect:
        # Импортируем тестируемую функцию
        from app.utils.rabbit_utils import get_connection
        
        # Настраиваем мок для имитации ошибки
        mock_connect.side_effect = aio_pika.exceptions.AMQPError("Connection error")
        
        # Вызываем тестируемую функцию и ожидаем исключение
        with pytest.raises(aio_pika.exceptions.AMQPError):
            await get_connection()

@pytest.mark.asyncio
async def test_close_connection():
    """Тест закрытия соединения с RabbitMQ."""
    # Импортируем тестируемую функцию
    from app.utils.rabbit_utils import close_connection
    
    # Создаем мок для соединения
    connection_mock = AsyncMock()
    connection_mock.is_closed = False
    
    # Вызываем тестируемую функцию
    with patch('builtins.print') as mock_print:
        await close_connection(connection_mock)
    
    # Проверяем, что метод close был вызван
    connection_mock.close.assert_called_once()
    # Проверяем, что было выведено сообщение
    mock_print.assert_called_once_with("Соединение с RabbitMQ закрыто")

@pytest.mark.asyncio
async def test_close_connection_already_closed():
    """Тест закрытия уже закрытого соединения с RabbitMQ."""
    # Импортируем тестируемую функцию
    from app.utils.rabbit_utils import close_connection
    
    # Создаем мок для соединения
    connection_mock = AsyncMock()
    connection_mock.is_closed = True
    
    # Вызываем тестируемую функцию
    await close_connection(connection_mock)
    
    # Проверяем, что метод close не был вызван
    connection_mock.close.assert_not_called()

@pytest.mark.asyncio
async def test_close_connection_none():
    """Тест закрытия несуществующего соединения с RabbitMQ."""
    # Импортируем тестируемую функцию
    from app.utils.rabbit_utils import close_connection
    
    # Вызываем тестируемую функцию с None
    await close_connection(None)
    
    # Если дошли сюда, значит функция не выбросила исключение

@pytest.mark.asyncio
async def test_declare_queue(patch_settings):
    """Тест объявления очереди в RabbitMQ."""
    # Импортируем тестируемую функцию
    from app.utils.rabbit_utils import declare_queue
    
    # Создаем моки
    channel_mock = AsyncMock()
    queue_mock = AsyncMock()
    channel_mock.declare_queue.return_value = queue_mock
    
    # Название очереди для теста
    queue_name = "test-queue"
    
    # Вызываем тестируемую функцию
    result = await declare_queue(channel_mock, queue_name)
    
    # Проверяем, что функция вернула созданную очередь
    assert result == queue_mock
    
    # Проверяем, что метод declare_queue был вызван с правильными параметрами
    channel_mock.declare_queue.assert_called_once_with(
        queue_name,
        durable=True,
        arguments={
            "x-dead-letter-exchange": TEST_DLX_NAME,
            "x-dead-letter-routing-key": queue_name
        }
    )

@pytest.mark.asyncio
async def test_declare_queue_channel_closed(patch_settings):
    """Тест объявления очереди при закрытом канале."""
    # Импортируем тестируемую функцию
    from app.utils.rabbit_utils import declare_queue
    
    # Создаем моки
    channel_mock = AsyncMock()
    queue_mock = AsyncMock()
    
    # Настраиваем, чтобы первый вызов выбрасывал исключение, а второй возвращал очередь
    channel_mock.declare_queue.side_effect = [
        ChannelClosed("Queue with different parameters already exists"),
        queue_mock
    ]
    
    # Название очереди для теста
    queue_name = "test-queue"
    
    # Вызываем тестируемую функцию
    with patch('builtins.print') as mock_print:
        result = await declare_queue(channel_mock, queue_name)
    
    # Проверяем, что функция вернула созданную очередь
    assert result == queue_mock
    
    # Проверяем, что метод declare_queue был вызван дважды с разными параметрами
    assert channel_mock.declare_queue.call_count == 2
    
    # Проверяем, что первый вызов был с нужными параметрами
    first_call_args = channel_mock.declare_queue.call_args_list[0]
    assert first_call_args[0][0] == queue_name
    assert first_call_args[1]["durable"] is True
    assert "x-dead-letter-exchange" in first_call_args[1]["arguments"]
    
    # Проверяем, что второй вызов был с параметром passive=True
    second_call_args = channel_mock.declare_queue.call_args_list[1]
    assert second_call_args[0][0] == queue_name
    assert second_call_args[1]["passive"] is True
    
    # Проверяем, что было выведено сообщение об ошибке
    mock_print.assert_called_once()
    assert f"Очередь {queue_name} уже существует" in mock_print.call_args[0][0]

@pytest.mark.asyncio
async def test_declare_queue_other_exception(patch_settings):
    """Тест объявления очереди при возникновении другой ошибки."""
    # Импортируем тестируемую функцию
    from app.utils.rabbit_utils import declare_queue
    
    # Создаем мок
    channel_mock = AsyncMock()
    
    # Настраиваем, чтобы вызов выбрасывал исключение
    error_message = "Другая ошибка RabbitMQ"
    channel_mock.declare_queue.side_effect = aio_pika.exceptions.AMQPError(error_message)
    
    # Название очереди для теста
    queue_name = "test-queue"
    
    # Вызываем тестируемую функцию и ожидаем исключение
    with pytest.raises(aio_pika.exceptions.AMQPError) as excinfo:
        await declare_queue(channel_mock, queue_name)
    
    assert str(excinfo.value) == error_message 