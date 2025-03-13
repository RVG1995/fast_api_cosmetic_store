import pytest
import pytest_asyncio
import asyncio
from unittest.mock import patch, AsyncMock, MagicMock
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from product_service.main import app
from product_service.database import get_session
from product_service.auth import require_admin

# Переопределяем функцию get_session для всех тестов
@pytest.fixture(scope="session")
def mock_connection():
    """Мок для подключения к базе данных"""
    return AsyncMock()

@pytest.fixture(scope="function")
def mock_session():
    """Мок для сессии базы данных"""
    session = AsyncMock(spec=AsyncSession)
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    session.close = AsyncMock()
    
    # Настройка функции add() для ProductModel
    def add_mock(obj):
        # Устанавливаем id и in_stock для новой модели
        if hasattr(obj, 'id') and obj.id is None:
            obj.id = 1
        if hasattr(obj, 'in_stock'):
            obj.in_stock = True
        return None
    
    session.add = MagicMock(side_effect=add_mock)
    
    return session

# Мок для аутентификации администратора
@pytest_asyncio.fixture
async def mock_admin():
    """Мок для require_admin, который всегда возвращает админа"""
    admin_user = {"user_id": 1, "is_admin": True}
    
    async def mock_admin_func():
        return admin_user
    
    # Сохраняем оригинальную функцию
    original = app.dependency_overrides.get(require_admin)
    
    # Устанавливаем мок
    app.dependency_overrides[require_admin] = mock_admin_func
    
    # Патчим функцию в Auth модуле
    with patch("product_service.auth.require_admin", return_value=admin_user):
        yield
    
    # Восстанавливаем оригинальную зависимость или удаляем переопределение
    if original:
        app.dependency_overrides[require_admin] = original
    else:
        del app.dependency_overrides[require_admin]

# Патчим get_session для всех тестов
@pytest_asyncio.fixture(autouse=True)
async def mock_db(monkeypatch, mock_session):
    """Патчим get_session для всех тестов"""
    async def mock_get_session():
        yield mock_session
    
    # Патчим get_session в модуле main
    monkeypatch.setattr("product_service.main.get_session", mock_get_session)
    
    yield mock_session

# Настраиваем pytest.ini в коде - это не работает, поэтому создаем отдельный файл 

# Создаем тестовую базу данных в памяти для тестов
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

# Настраиваем область видимости цикла событий для всех асинхронных тестов
def pytest_configure(config):
    """Устанавливаем глобальный параметр loop_scope для всех асинхронных тестов"""
    config.option.asyncio_default_fixture_loop_scope = "session"

# Фикстура для создания тестового движка базы данных
@pytest.fixture(scope="session")
async def test_engine():
    """Создает тестовый engine для базы данных"""
    engine = create_async_engine(TEST_DATABASE_URL, echo=True)
    yield engine
    await engine.dispose()

@pytest.fixture
async def test_session_factory(test_engine):
    """Создает фабрику сессий для тестов"""
    from product_service.models import Base
    
    # Создаем все таблицы
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    
    # Создаем фабрику сессий
    async_session = sessionmaker(
        test_engine, class_=AsyncSession, expire_on_commit=False
    )
    
    # Возвращаем фабрику
    return async_session

@pytest.fixture
async def test_session(test_session_factory):
    """Создает тестовую сессию для каждого теста"""
    async with test_session_factory() as session:
        yield session
        # Откатываем изменения в конце теста
        await session.rollback()

@pytest.fixture
async def override_get_session(test_session_factory):
    """Переопределяет зависимость получения сессии для FastAPI"""
    async def _override_get_session():
        async with test_session_factory() as session:
            yield session
    
    # Сохраняем оригинальную зависимость
    original = app.dependency_overrides.get(get_session)
    
    # Устанавливаем нашу тестовую зависимость
    app.dependency_overrides[get_session] = _override_get_session
    
    # Возвращаем управление для теста
    yield
    
    # Восстанавливаем оригинальную зависимость или удаляем переопределение
    if original:
        app.dependency_overrides[get_session] = original
    else:
        del app.dependency_overrides[get_session] 