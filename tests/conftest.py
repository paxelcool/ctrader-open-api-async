"""Конфигурация pytest для тестов cTrader Open API Async."""

import pytest
import asyncio
from typing import Generator


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Создает event loop для всей сессии тестирования."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def mock_credentials():
    """Мок учетных данных для тестов."""
    return {
        "client_id": "test_client_id",
        "client_secret": "test_client_secret", 
        "access_token": "test_access_token"
    }


def pytest_configure(config):
    """Конфигурация pytest."""
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests (may require network)"
    )
    config.addinivalue_line(
        "markers", "slow: marks tests as slow running"
    )


def pytest_collection_modifyitems(config, items):
    """Модифицирует коллекцию тестов."""
    # Добавляем маркер asyncio для всех async тестов
    for item in items:
        if asyncio.iscoroutinefunction(item.function):
            item.add_marker(pytest.mark.asyncio) 