import pytest
import pytest_asyncio
import asyncio
from unittest.mock import patch, AsyncMock, MagicMock
from sqlalchemy.ext.asyncio import AsyncSession

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