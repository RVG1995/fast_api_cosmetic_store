"""Тесты для модуля отправки email-сообщений через RabbitMQ."""

import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch, call
import json
import aio_pika

# Импортируем тестируемый модуль
from app.services import email_service
from app.services.email_service import send_email_activation_message, send_password_reset_email

# Константы для тестов
TEST_USER_ID = "12345"
TEST_EMAIL = "test@example.com"
TEST_ACTIVATION_TOKEN = "test_activation_token_123"
TEST_RESET_TOKEN = "test_reset_token_456"
TEST_ACTIVATION_LINK = f"http://localhost:3000/activate/{TEST_ACTIVATION_TOKEN}"
TEST_RESET_LINK = f"http://localhost:3000/reset-password/{TEST_RESET_TOKEN}"

# Моки для тестирования
@pytest.fixture
def mock_connection():
    """Мок соединения с RabbitMQ."""
    return AsyncMock()

@pytest.fixture
def mock_channel():
    """Мок канала RabbitMQ."""
    channel = AsyncMock()
    # Настраиваем default_exchange
    channel.default_exchange = AsyncMock()
    channel.default_exchange.publish = AsyncMock()
    return channel

@pytest.fixture
def mock_queue():
    """Мок очереди RabbitMQ."""
    queue = AsyncMock()
    queue.name = "test_queue"
    return queue

@pytest.fixture
def mock_get_connection():
    """Патч для функции get_connection."""
    with patch('app.services.email_service.get_connection') as mock:
        yield mock

@pytest.fixture
def mock_close_connection():
    """Патч для функции close_connection."""
    with patch('app.services.email_service.close_connection') as mock:
        yield mock

@pytest.fixture
def mock_declare_queue():
    """Патч для функции declare_queue."""
    with patch('app.services.email_service.declare_queue') as mock:
        yield mock

# Тесты для send_email_activation_message
@pytest.mark.asyncio
async def test_send_email_activation_message_success(
    mock_connection, mock_channel, mock_queue, 
    mock_get_connection, mock_close_connection, mock_declare_queue
):
    """Тест успешной отправки сообщения для активации аккаунта."""
    # Настраиваем моки
    mock_get_connection.return_value = mock_connection
    mock_connection.channel.return_value = mock_channel
    mock_declare_queue.return_value = mock_queue
    
    # Вызываем тестируемую функцию
    await send_email_activation_message(
        user_id=TEST_USER_ID,
        email=TEST_EMAIL,
        activation_link=TEST_ACTIVATION_LINK
    )
    
    # Проверяем, что функции были вызваны с правильными аргументами
    mock_get_connection.assert_called_once()
    mock_connection.channel.assert_called_once()
    mock_declare_queue.assert_called_once_with(mock_channel, "registration_message")
    mock_close_connection.assert_called_once_with(mock_connection)
    
    # Проверяем, что сообщение было отправлено с правильными данными
    mock_channel.default_exchange.publish.assert_called_once()
    call_args = mock_channel.default_exchange.publish.call_args
    
    # Проверяем аргументы вызова
    message = call_args[0][0]
    assert isinstance(message, aio_pika.Message)
    
    # Проверяем данные сообщения
    message_body = json.loads(message.body.decode())
    assert message_body["user_id"] == TEST_USER_ID
    assert message_body["email"] == TEST_EMAIL
    assert message_body["activation_link"] == TEST_ACTIVATION_LINK
    
    # Проверяем routing_key (имя очереди)
    routing_key = call_args[1]["routing_key"]
    assert routing_key == mock_queue.name
    
    # Проверяем режим доставки
    assert message.delivery_mode == aio_pika.DeliveryMode.PERSISTENT

@pytest.mark.asyncio
async def test_send_email_activation_message_exception_handled(
    mock_connection, mock_get_connection, mock_close_connection
):
    """Тест вызова close_connection при возникновении ошибки в отправке сообщения."""
    # Настраиваем моки для имитации исключения
    mock_get_connection.return_value = mock_connection
    mock_connection.channel.side_effect = Exception("Connection error")
    
    # Вызываем тестируемую функцию и ожидаем исключение
    with pytest.raises(Exception):
        await send_email_activation_message(
            user_id=TEST_USER_ID,
            email=TEST_EMAIL,
            activation_link=TEST_ACTIVATION_LINK
        )
    
    # Проверяем, что соединение было закрыто, несмотря на исключение
    mock_close_connection.assert_called_once_with(mock_connection)

# Тесты для send_password_reset_email
@pytest.mark.asyncio
async def test_send_password_reset_email_success(
    mock_connection, mock_channel, mock_queue, 
    mock_get_connection, mock_close_connection, mock_declare_queue
):
    """Тест успешной отправки сообщения для сброса пароля."""
    # Настраиваем моки
    mock_get_connection.return_value = mock_connection
    mock_connection.channel.return_value = mock_channel
    mock_declare_queue.return_value = mock_queue
    
    # Вызываем тестируемую функцию
    await send_password_reset_email(
        user_id=TEST_USER_ID,
        email=TEST_EMAIL,
        reset_token=TEST_RESET_TOKEN
    )
    
    # Проверяем, что функции были вызваны с правильными аргументами
    mock_get_connection.assert_called_once()
    mock_connection.channel.assert_called_once()
    mock_declare_queue.assert_called_once_with(mock_channel, "password_reset_message")
    mock_close_connection.assert_called_once_with(mock_connection)
    
    # Проверяем, что сообщение было отправлено с правильными данными
    mock_channel.default_exchange.publish.assert_called_once()
    call_args = mock_channel.default_exchange.publish.call_args
    
    # Проверяем аргументы вызова
    message = call_args[0][0]
    assert isinstance(message, aio_pika.Message)
    
    # Проверяем данные сообщения
    message_body = json.loads(message.body.decode())
    assert message_body["user_id"] == TEST_USER_ID
    assert message_body["email"] == TEST_EMAIL
    assert TEST_RESET_TOKEN in message_body["reset_link"]
    
    # Проверяем routing_key (имя очереди)
    routing_key = call_args[1]["routing_key"]
    assert routing_key == mock_queue.name
    
    # Проверяем режим доставки
    assert message.delivery_mode == aio_pika.DeliveryMode.PERSISTENT

@pytest.mark.asyncio
async def test_send_password_reset_email_exception_handled(
    mock_connection, mock_get_connection, mock_close_connection
):
    """Тест вызова close_connection при возникновении ошибки в отправке сообщения для сброса пароля."""
    # Настраиваем моки для имитации исключения
    mock_get_connection.return_value = mock_connection
    mock_connection.channel.side_effect = Exception("Connection error")
    
    # Вызываем тестируемую функцию и ожидаем исключение
    with pytest.raises(Exception):
        await send_password_reset_email(
            user_id=TEST_USER_ID,
            email=TEST_EMAIL,
            reset_token=TEST_RESET_TOKEN
        )
    
    # Проверяем, что соединение было закрыто, несмотря на исключение
    mock_close_connection.assert_called_once_with(mock_connection)

# Тест для проверки правильного формирования ссылки для сброса пароля
@pytest.mark.asyncio
async def test_reset_link_formation(
    mock_connection, mock_channel, mock_queue, 
    mock_get_connection, mock_close_connection, mock_declare_queue
):
    """Тест правильного формирования ссылки для сброса пароля."""
    # Настраиваем моки
    mock_get_connection.return_value = mock_connection
    mock_connection.channel.return_value = mock_channel
    mock_declare_queue.return_value = mock_queue
    
    # Вызываем тестируемую функцию
    await send_password_reset_email(
        user_id=TEST_USER_ID,
        email=TEST_EMAIL,
        reset_token=TEST_RESET_TOKEN
    )
    
    # Получаем отправленное сообщение
    call_args = mock_channel.default_exchange.publish.call_args
    message = call_args[0][0]
    message_body = json.loads(message.body.decode())
    
    # Проверяем, что ссылка для сброса пароля сформирована правильно
    expected_reset_link = f"http://localhost:3000/reset-password/{TEST_RESET_TOKEN}"
    assert message_body["reset_link"] == expected_reset_link 