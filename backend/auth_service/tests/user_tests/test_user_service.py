"""Тесты для модуля управления пользователями (user_service.py)."""

import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch
import httpx
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import SQLAlchemyError

# Импортируем тестируемый модуль
from app.services.auth.user_service import UserService, user_service
from app.services.auth.cache_service import cache_service
from models import UserModel

# Константы для тестов
TEST_USER_ID = 1
TEST_EMAIL = "test@example.com"
TEST_PASSWORD = "password123"
TEST_HASHED_PASSWORD = "$2b$12$testpasswordhash"  # Правильный формат bcrypt хеша
TEST_FIRST_NAME = "Test"
TEST_LAST_NAME = "User"
TEST_ACTIVATION_TOKEN = "test_activation_token_123"

# Фикстуры для тестирования
@pytest_asyncio.fixture
async def mock_user():
    """Мок для объекта пользователя."""
    user = MagicMock(spec=UserModel)
    user.id = TEST_USER_ID
    user.first_name = TEST_FIRST_NAME
    user.last_name = TEST_LAST_NAME
    user.email = TEST_EMAIL
    user.hashed_password = TEST_HASHED_PASSWORD
    user.is_active = True
    user.is_admin = False
    user.is_super_admin = False
    user.activation_token = None
    user.personal_data_agreement = True
    user.notification_agreement = True
    user.last_login = datetime.now(timezone.utc)
    user.activate = AsyncMock()
    return user

@pytest_asyncio.fixture
async def mock_inactive_user():
    """Мок для неактивного объекта пользователя."""
    user = MagicMock(spec=UserModel)
    user.id = TEST_USER_ID + 1
    user.first_name = TEST_FIRST_NAME
    user.last_name = TEST_LAST_NAME
    user.email = "inactive@example.com"
    user.hashed_password = TEST_HASHED_PASSWORD
    user.is_active = False
    user.is_admin = False
    user.is_super_admin = False
    user.activation_token = TEST_ACTIVATION_TOKEN
    user.personal_data_agreement = True
    user.notification_agreement = True
    user.last_login = None
    user.activate = AsyncMock()
    return user

# Патчи для user_service методов
@pytest.fixture
def patch_get_user_by_id():
    with patch.object(UserModel, 'get_by_id') as mock:
        yield mock

@pytest.fixture
def patch_get_user_by_email():
    with patch.object(UserModel, 'get_by_email') as mock:
        yield mock

@pytest.fixture
def patch_get_user_by_activation_token():
    with patch.object(UserModel, 'get_by_activation_token') as mock:
        yield mock

@pytest.fixture
def patch_cache_delete():
    with patch.object(cache_service, 'delete', new_callable=AsyncMock) as mock:
        yield mock

@pytest.fixture
def patch_get_password_hash():
    with patch('app.services.auth.user_service.get_password_hash', new_callable=AsyncMock) as mock:
        mock.return_value = TEST_HASHED_PASSWORD
        yield mock

@pytest.fixture
def patch_verify_password():
    with patch('app.services.auth.user_service.verify_password', new_callable=AsyncMock) as mock:
        yield mock

@pytest.fixture
def patch_send_email_activation_message():
    with patch('app.services.auth.user_service.send_email_activation_message', new_callable=AsyncMock) as mock:
        yield mock

# Тесты для get_user_by_id
@pytest.mark.asyncio
async def test_get_user_by_id_success(mock_session, mock_user, patch_get_user_by_id):
    """Тест успешного получения пользователя по ID."""
    # Настраиваем мок для имитации успешного запроса
    patch_get_user_by_id.return_value = mock_user
    
    # Вызываем тестируемый метод
    result = await UserService.get_user_by_id(mock_session, TEST_USER_ID)
    
    # Проверяем, что метод вернул ожидаемый результат
    assert result == mock_user
    
    # Проверяем, что метод get_by_id был вызван с правильными аргументами
    patch_get_user_by_id.assert_called_once_with(mock_session, TEST_USER_ID)

@pytest.mark.asyncio
async def test_get_user_by_id_not_found(mock_session, patch_get_user_by_id):
    """Тест получения пользователя по ID, когда пользователь не найден."""
    # Настраиваем мок для имитации отсутствия пользователя
    patch_get_user_by_id.return_value = None
    
    # Вызываем тестируемый метод
    result = await UserService.get_user_by_id(mock_session, TEST_USER_ID)
    
    # Проверяем, что метод вернул None
    assert result is None
    
    # Проверяем, что метод get_by_id был вызван с правильными аргументами
    patch_get_user_by_id.assert_called_once_with(mock_session, TEST_USER_ID)

# Тесты для get_user_by_email
@pytest.mark.asyncio
async def test_get_user_by_email_success(mock_session, mock_user, patch_get_user_by_email):
    """Тест успешного получения пользователя по email."""
    # Настраиваем мок для имитации успешного запроса
    patch_get_user_by_email.return_value = mock_user
    
    # Вызываем тестируемый метод
    result = await UserService.get_user_by_email(mock_session, TEST_EMAIL)
    
    # Проверяем, что метод вернул ожидаемый результат
    assert result == mock_user
    
    # Проверяем, что метод get_by_email был вызван с правильными аргументами
    patch_get_user_by_email.assert_called_once_with(mock_session, TEST_EMAIL)

@pytest.mark.asyncio
async def test_get_user_by_email_not_found(mock_session, patch_get_user_by_email):
    """Тест получения пользователя по email, когда пользователь не найден."""
    # Настраиваем мок для имитации отсутствия пользователя
    patch_get_user_by_email.return_value = None
    
    # Вызываем тестируемый метод
    result = await UserService.get_user_by_email(mock_session, TEST_EMAIL)
    
    # Проверяем, что метод вернул None
    assert result is None
    
    # Проверяем, что метод get_by_email был вызван с правильными аргументами
    patch_get_user_by_email.assert_called_once_with(mock_session, TEST_EMAIL)

# Тесты для create_user
@pytest.mark.asyncio
async def test_create_user_success(mock_session, patch_get_password_hash, patch_cache_delete):
    """Тест успешного создания пользователя."""
    # Настраиваем мок для имитации успешного хеширования пароля
    patch_get_password_hash.return_value = TEST_HASHED_PASSWORD
    
    # Вызываем тестируемый метод
    with patch('secrets.token_urlsafe', return_value=TEST_ACTIVATION_TOKEN):
        user, token = await UserService.create_user(
            session=mock_session,
            first_name=TEST_FIRST_NAME,
            last_name=TEST_LAST_NAME,
            email=TEST_EMAIL,
            password=TEST_PASSWORD,
            is_active=False,
            personal_data_agreement=True,
            notification_agreement=True
        )
    
    # Проверяем, что add был вызван
    mock_session.add.assert_called_once()
    
    # Проверяем, что commit был вызван
    mock_session.commit.assert_called_once()
    
    # Проверяем, что refresh был вызван
    mock_session.refresh.assert_called_once()
    
    # Проверяем, что был вызван метод delete кэша
    cache_key = f"get_user_by_email:{TEST_EMAIL}"
    patch_cache_delete.assert_called_once_with(cache_key)
    
    # Проверяем, что метод вернул объект пользователя и токен
    assert user is not None
    assert token is not None
    assert isinstance(token, str)
    
    # Проверяем, что хеширование пароля было вызвано с правильными аргументами
    patch_get_password_hash.assert_called_once_with(TEST_PASSWORD)
    
    # Проверяем, что тип объекта пользователя - UserModel
    added_user = mock_session.add.call_args.args[0]
    assert isinstance(added_user, UserModel)
    assert added_user.first_name == TEST_FIRST_NAME
    assert added_user.last_name == TEST_LAST_NAME
    assert added_user.email == TEST_EMAIL
    assert added_user.hashed_password == TEST_HASHED_PASSWORD
    assert added_user.is_active is False

@pytest.mark.asyncio
async def test_create_user_active_status(mock_session, patch_get_password_hash, patch_cache_delete):
    """Тест создания активного пользователя."""
    # Настраиваем мок для имитации успешного хеширования пароля
    patch_get_password_hash.return_value = TEST_HASHED_PASSWORD
    
    # Вызываем тестируемый метод с is_active=True
    user, token = await UserService.create_user(
        session=mock_session,
        first_name=TEST_FIRST_NAME,
        last_name=TEST_LAST_NAME,
        email=TEST_EMAIL,
        password=TEST_PASSWORD,
        is_active=True,
        personal_data_agreement=True,
        notification_agreement=True
    )
    
    # Проверяем, что пользователь активен и токен None
    added_user = mock_session.add.call_args.args[0]
    assert added_user.is_active is True
    assert added_user.activation_token is None

@pytest.mark.asyncio
async def test_create_user_error(mock_session, patch_get_password_hash):
    """Тест создания пользователя при возникновении ошибки."""
    # Настраиваем мок для имитации ошибки при коммите
    mock_session.commit.side_effect = SQLAlchemyError("Database error")
    
    # Вызываем тестируемый метод и ожидаем исключение
    with pytest.raises(SQLAlchemyError):
        await UserService.create_user(
            session=mock_session,
            first_name=TEST_FIRST_NAME,
            last_name=TEST_LAST_NAME,
            email=TEST_EMAIL,
            password=TEST_PASSWORD
        )
    
    # Проверяем, что add был вызван
    mock_session.add.assert_called_once()
    
    # Проверяем, что commit был вызван
    mock_session.commit.assert_called_once()

# Тесты для activate_user
@pytest.mark.asyncio
async def test_activate_user_success(mock_session, mock_inactive_user, patch_get_user_by_activation_token, patch_cache_delete):
    """Тест успешной активации пользователя."""
    # Настраиваем мок для имитации успешного получения пользователя по токену
    patch_get_user_by_activation_token.return_value = mock_inactive_user
    
    # Вызываем тестируемый метод
    result = await UserService.activate_user(mock_session, TEST_ACTIVATION_TOKEN)
    
    # Проверяем, что метод вернул ожидаемый результат
    assert result == mock_inactive_user
    
    # Проверяем, что метод get_by_activation_token был вызван с правильными аргументами
    patch_get_user_by_activation_token.assert_called_once_with(mock_session, TEST_ACTIVATION_TOKEN)
    
    # Проверяем, что метод activate пользователя был вызван
    mock_inactive_user.activate.assert_called_once_with(mock_session)
    
    # Проверяем, что кэш был инвалидирован
    assert patch_cache_delete.call_count == 2
    
    # Проверяем, что кэш был инвалидирован для правильных ключей
    user_cache_key = f"get_user_by_id:{mock_inactive_user.id}"
    email_cache_key = f"get_user_by_email:{mock_inactive_user.email}"
    patch_cache_delete.assert_any_call(user_cache_key)
    patch_cache_delete.assert_any_call(email_cache_key)

@pytest.mark.asyncio
async def test_activate_user_not_found(mock_session, patch_get_user_by_activation_token):
    """Тест активации пользователя, когда пользователь не найден."""
    # Настраиваем мок для имитации отсутствия пользователя
    patch_get_user_by_activation_token.return_value = None
    
    # Вызываем тестируемый метод
    result = await UserService.activate_user(mock_session, TEST_ACTIVATION_TOKEN)
    
    # Проверяем, что метод вернул None
    assert result is None
    
    # Проверяем, что метод get_by_activation_token был вызван с правильными аргументами
    patch_get_user_by_activation_token.assert_called_once_with(mock_session, TEST_ACTIVATION_TOKEN)

# Тесты для verify_credentials
@pytest.mark.asyncio
async def test_verify_credentials_success(mock_session, mock_user, patch_get_user_by_email, patch_verify_password):
    """Тест успешной проверки учетных данных."""
    # Настраиваем моки для имитации успешной проверки
    patch_get_user_by_email.return_value = mock_user
    patch_verify_password.return_value = True
    
    # Вызываем тестируемый метод
    result = await UserService.verify_credentials(mock_session, TEST_EMAIL, TEST_PASSWORD)
    
    # Проверяем, что метод вернул ожидаемый результат
    assert result == mock_user
    
    # Проверяем, что метод get_user_by_email был вызван с правильными аргументами
    patch_get_user_by_email.assert_called_once_with(mock_session, TEST_EMAIL)
    
    # Проверяем, что метод verify_password был вызван с правильными аргументами
    patch_verify_password.assert_called_once_with(TEST_PASSWORD, mock_user.hashed_password)

@pytest.mark.asyncio
async def test_verify_credentials_user_not_found(mock_session, patch_get_user_by_email):
    """Тест проверки учетных данных, когда пользователь не найден."""
    # Настраиваем мок для имитации отсутствия пользователя
    patch_get_user_by_email.return_value = None
    
    # Вызываем тестируемый метод
    result = await UserService.verify_credentials(mock_session, TEST_EMAIL, TEST_PASSWORD)
    
    # Проверяем, что метод вернул None
    assert result is None
    
    # Проверяем, что метод get_user_by_email был вызван с правильными аргументами
    patch_get_user_by_email.assert_called_once_with(mock_session, TEST_EMAIL)

@pytest.mark.asyncio
async def test_verify_credentials_wrong_password(mock_session, mock_user, patch_get_user_by_email, patch_verify_password):
    """Тест проверки учетных данных с неверным паролем."""
    # Настраиваем моки для имитации неверного пароля
    patch_get_user_by_email.return_value = mock_user
    patch_verify_password.return_value = False
    
    # Вызываем тестируемый метод
    result = await UserService.verify_credentials(mock_session, TEST_EMAIL, "wrong_password")
    
    # Проверяем, что метод вернул None
    assert result is None
    
    # Проверяем, что методы были вызваны с правильными аргументами
    patch_get_user_by_email.assert_called_once_with(mock_session, TEST_EMAIL)
    patch_verify_password.assert_called_once_with("wrong_password", mock_user.hashed_password)

@pytest.mark.asyncio
async def test_verify_credentials_inactive_user(mock_session, mock_inactive_user, patch_get_user_by_email, patch_verify_password):
    """Тест проверки учетных данных неактивного пользователя."""
    # Настраиваем моки для имитации успешной проверки пароля, но неактивного пользователя
    patch_get_user_by_email.return_value = mock_inactive_user
    patch_verify_password.return_value = True
    
    # Вызываем тестируемый метод
    result = await UserService.verify_credentials(mock_session, mock_inactive_user.email, TEST_PASSWORD)
    
    # Проверяем, что метод вернул None
    assert result is None
    
    # Проверяем, что методы были вызваны с правильными аргументами
    patch_get_user_by_email.assert_called_once_with(mock_session, mock_inactive_user.email)
    patch_verify_password.assert_called_once_with(TEST_PASSWORD, mock_inactive_user.hashed_password)

# Тесты для update_last_login
@pytest.mark.asyncio
async def test_update_last_login_success(mock_session, mock_user, patch_get_user_by_id, patch_cache_delete):
    """Тест успешного обновления времени последнего входа."""
    # Настраиваем мок для имитации успешного получения пользователя
    patch_get_user_by_id.return_value = mock_user
    
    # Вызываем тестируемый метод
    result = await UserService.update_last_login(mock_session, TEST_USER_ID)
    
    # Проверяем, что метод вернул True
    assert result is True
    
    # Проверяем, что метод get_user_by_id был вызван с правильными аргументами
    patch_get_user_by_id.assert_called_once_with(mock_session, TEST_USER_ID)
    
    # Проверяем, что время последнего входа было обновлено
    assert mock_user.last_login is not None
    
    # Проверяем, что был сделан коммит
    mock_session.commit.assert_called_once()
    
    # Проверяем, что кэш был инвалидирован
    assert patch_cache_delete.call_count == 2
    
    # Проверяем, что кэш был инвалидирован для правильных ключей
    user_cache_key = f"get_user_by_id:{TEST_USER_ID}"
    email_cache_key = f"get_user_by_email:{mock_user.email}"
    patch_cache_delete.assert_any_call(user_cache_key)
    patch_cache_delete.assert_any_call(email_cache_key)

@pytest.mark.asyncio
async def test_update_last_login_user_not_found(mock_session, patch_get_user_by_id):
    """Тест обновления времени последнего входа, когда пользователь не найден."""
    # Настраиваем мок для имитации отсутствия пользователя
    patch_get_user_by_id.return_value = None
    
    # Вызываем тестируемый метод
    result = await UserService.update_last_login(mock_session, TEST_USER_ID)
    
    # Проверяем, что метод вернул False
    assert result is False
    
    # Проверяем, что метод get_user_by_id был вызван с правильными аргументами
    patch_get_user_by_id.assert_called_once_with(mock_session, TEST_USER_ID)
    
    # Проверяем, что коммит не был вызван
    mock_session.commit.assert_not_called()

@pytest.mark.asyncio
async def test_update_last_login_error(mock_session, mock_user, patch_get_user_by_id):
    """Тест обновления времени последнего входа при возникновении ошибки."""
    # Настраиваем моки для имитации ошибки
    patch_get_user_by_id.return_value = mock_user
    mock_session.commit.side_effect = SQLAlchemyError("Database error")
    
    # Вызываем тестируемый метод
    result = await UserService.update_last_login(mock_session, TEST_USER_ID)
    
    # Проверяем, что метод вернул False
    assert result is False
    
    # Проверяем, что метод get_user_by_id был вызван с правильными аргументами
    patch_get_user_by_id.assert_called_once_with(mock_session, TEST_USER_ID)
    
    # Проверяем, что коммит был вызван
    mock_session.commit.assert_called_once()

# Тесты для change_password
@pytest.mark.asyncio
async def test_change_password_success(mock_session, mock_user, patch_get_user_by_id, patch_get_password_hash, patch_cache_delete):
    """Тест успешной смены пароля."""
    # Настраиваем моки для имитации успешного получения пользователя и хеширования пароля
    patch_get_user_by_id.return_value = mock_user
    new_hashed_password = "$2b$12$newhashpassword"
    patch_get_password_hash.return_value = new_hashed_password
    
    # Вызываем тестируемый метод
    result = await UserService.change_password(mock_session, TEST_USER_ID, "new_password")
    
    # Проверяем, что метод вернул True
    assert result is True
    
    # Проверяем, что метод get_user_by_id был вызван с правильными аргументами
    patch_get_user_by_id.assert_called_once_with(mock_session, TEST_USER_ID)
    
    # Проверяем, что метод get_password_hash был вызван с правильными аргументами
    patch_get_password_hash.assert_called_once_with("new_password")
    
    # Проверяем, что пароль был обновлен
    assert mock_user.hashed_password == new_hashed_password
    
    # Проверяем, что был сделан коммит
    mock_session.commit.assert_called_once()
    
    # Проверяем, что кэш был инвалидирован
    assert patch_cache_delete.call_count == 2
    
    # Проверяем, что кэш был инвалидирован для правильных ключей
    user_cache_key = f"get_user_by_id:{TEST_USER_ID}"
    email_cache_key = f"get_user_by_email:{mock_user.email}"
    patch_cache_delete.assert_any_call(user_cache_key)
    patch_cache_delete.assert_any_call(email_cache_key)

@pytest.mark.asyncio
async def test_change_password_user_not_found(mock_session, patch_get_user_by_id):
    """Тест смены пароля, когда пользователь не найден."""
    # Настраиваем мок для имитации отсутствия пользователя
    patch_get_user_by_id.return_value = None
    
    # Вызываем тестируемый метод
    result = await UserService.change_password(mock_session, TEST_USER_ID, "new_password")
    
    # Проверяем, что метод вернул False
    assert result is False
    
    # Проверяем, что метод get_user_by_id был вызван с правильными аргументами
    patch_get_user_by_id.assert_called_once_with(mock_session, TEST_USER_ID)

@pytest.mark.asyncio
async def test_change_password_error(mock_session, mock_user, patch_get_user_by_id, patch_get_password_hash):
    """Тест смены пароля при возникновении ошибки."""
    # Настраиваем моки для имитации ошибки
    patch_get_user_by_id.return_value = mock_user
    patch_get_password_hash.return_value = "$2b$12$newhashpassword"
    mock_session.commit.side_effect = SQLAlchemyError("Database error")
    
    # Вызываем тестируемый метод
    result = await UserService.change_password(mock_session, TEST_USER_ID, "new_password")
    
    # Проверяем, что метод вернул False
    assert result is False
    
    # Проверяем, что метод get_user_by_id был вызван с правильными аргументами
    patch_get_user_by_id.assert_called_once_with(mock_session, TEST_USER_ID)
    
    # Проверяем, что метод get_password_hash был вызван с правильными аргументами
    patch_get_password_hash.assert_called_once_with("new_password")
    
    # Проверяем, что коммит был вызван
    mock_session.commit.assert_called_once()

# Тесты для send_activation_email
@pytest.mark.asyncio
async def test_send_activation_email_success(patch_send_email_activation_message):
    """Тест успешной отправки письма активации."""
    # Настраиваем мок для имитации успешной отправки сообщения
    patch_send_email_activation_message.return_value = True
    
    # Вызываем тестируемый метод
    result = await UserService.send_activation_email(
        user_id=str(TEST_USER_ID),
        email=TEST_EMAIL,
        activation_token=TEST_ACTIVATION_TOKEN
    )
    
    # Проверяем, что метод вернул True
    assert result is True
    
    # Проверяем, что метод send_email_activation_message был вызван с правильными аргументами
    patch_send_email_activation_message.assert_called_once()
    args, _ = patch_send_email_activation_message.call_args
    assert args[0] == str(TEST_USER_ID)
    assert args[1] == TEST_EMAIL
    assert TEST_ACTIVATION_TOKEN in args[2]  # Проверяем, что токен содержится в ссылке активации

@pytest.mark.asyncio
async def test_send_activation_email_error(patch_send_email_activation_message):
    """Тест отправки письма активации при возникновении ошибки."""
    # Настраиваем мок для имитации ошибки при отправке сообщения
    patch_send_email_activation_message.side_effect = SQLAlchemyError("Email service error")
    
    # Вызываем тестируемый метод
    result = await UserService.send_activation_email(
        user_id=str(TEST_USER_ID),
        email=TEST_EMAIL,
        activation_token=TEST_ACTIVATION_TOKEN
    )
    
    # Проверяем, что метод вернул False
    assert result is False

# Тесты для activate_notifications
@pytest.mark.asyncio
async def test_activate_notifications_success():
    """Тест успешной активации уведомлений."""
    # Патчим httpx.AsyncClient для имитации HTTP запроса
    with patch('httpx.AsyncClient') as mock_client_class:
        # Настраиваем мок для имитации успешного ответа
        mock_client = AsyncMock()
        mock_client_class.return_value.__aenter__.return_value = mock_client
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"activated_count": 5}
        mock_client.post.return_value = mock_response
        
        # Вызываем тестируемый метод
        result = await UserService.activate_notifications(
            user_id=str(TEST_USER_ID),
            email=TEST_EMAIL,
            is_admin=False,
            service_token="test_service_token"
        )
        
        # Проверяем, что метод вернул True
        assert result is True
        
        # Проверяем, что метод post был вызван с правильными аргументами
        mock_client.post.assert_called_once()
        args, kwargs = mock_client.post.call_args
        
        # Проверяем URL и заголовки
        assert "/notifications/service/activate-notifications" in args[0]
        assert kwargs["headers"] == {"Authorization": "Bearer test_service_token"}
        
        # Проверяем данные запроса
        expected_data = {
            "user_id": str(TEST_USER_ID),
            "email": TEST_EMAIL,
            "is_admin": False
        }
        assert kwargs["json"] == expected_data

@pytest.mark.asyncio
async def test_activate_notifications_error_response():
    """Тест активации уведомлений при ошибке в ответе."""
    # Патчим httpx.AsyncClient для имитации HTTP запроса
    with patch('httpx.AsyncClient') as mock_client_class:
        # Настраиваем мок для имитации ошибочного ответа
        mock_client = AsyncMock()
        mock_client_class.return_value.__aenter__.return_value = mock_client
        
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.text = "Error activating notifications"
        mock_client.post.return_value = mock_response
        
        # Вызываем тестируемый метод
        result = await UserService.activate_notifications(
            user_id=str(TEST_USER_ID),
            email=TEST_EMAIL,
            is_admin=False,
            service_token="test_service_token"
        )
        
        # Проверяем, что метод вернул False
        assert result is False

@pytest.mark.asyncio
async def test_activate_notifications_request_error():
    """Тест активации уведомлений при ошибке запроса."""
    # Патчим httpx.AsyncClient для имитации HTTP запроса
    with patch('httpx.AsyncClient') as mock_client_class:
        # Настраиваем мок для имитации ошибки запроса
        mock_client = AsyncMock()
        mock_client_class.return_value.__aenter__.return_value = mock_client
        
        mock_client.post.side_effect = httpx.RequestError("Connection error")
        
        # Вызываем тестируемый метод
        result = await UserService.activate_notifications(
            user_id=str(TEST_USER_ID),
            email=TEST_EMAIL,
            is_admin=False,
            service_token="test_service_token"
        )
        
        # Проверяем, что метод вернул False
        assert result is False

@pytest.mark.asyncio
async def test_activate_notifications_no_token():
    """Тест активации уведомлений без токена."""
    # Вызываем тестируемый метод без токена
    result = await UserService.activate_notifications(
        user_id=str(TEST_USER_ID),
        email=TEST_EMAIL,
        is_admin=False,
        service_token=None
    )
    
    # Проверяем, что метод вернул False
    assert result is False 