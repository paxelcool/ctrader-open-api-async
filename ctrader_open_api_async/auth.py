"""Модуль для авторизации в cTrader API."""

from typing import Any, Dict, Optional
from urllib.parse import urlencode

import aiohttp

from .endpoints import EndPoints


class AsyncAuth:
    """Класс для работы с авторизацией cTrader API."""

    def __init__(self, app_client_id: str, app_client_secret: str, redirect_uri: str):
        """Инициализация авторизации.

        Args:
            app_client_id: ID приложения
            app_client_secret: Секрет приложения
            redirect_uri: URI для редиректа после авторизации
        """
        self.app_client_id = app_client_id
        self.app_client_secret = app_client_secret
        self.redirect_uri = redirect_uri
        self.session: Optional[aiohttp.ClientSession] = None

    async def __aenter__(self):
        """Асинхронный контекстный менеджер - вход."""
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Асинхронный контекстный менеджер - выход."""
        if self.session:
            await self.session.close()
            self.session = None

    def get_auth_uri(
        self, scope: str = "trading", base_uri: str = EndPoints.AUTH_URI
    ) -> str:
        """Получает URI для авторизации.

        Args:
            scope: Область доступа (по умолчанию "trading")
            base_uri: Базовый URI для авторизации

        Returns:
            Полный URI для авторизации
        """
        params = {
            "client_id": self.app_client_id,
            "redirect_uri": self.redirect_uri,
            "response_type": "code",
            "scope": scope,
        }
        return f"{base_uri}?{urlencode(params)}"

    async def get_token(
        self, auth_code: str, base_uri: str = EndPoints.TOKEN_URI
    ) -> Dict[str, Any]:
        """Получает токен доступа по коду авторизации.

        Args:
            auth_code: Код авторизации
            base_uri: Базовый URI для получения токена

        Returns:
            Словарь с данными токена

        Raises:
            ValueError: При ошибке получения токена
            RuntimeError: Если сессия не инициализирована
        """
        if not self.session:
            raise RuntimeError("Сессия не инициализирована. Используйте async with.")

        data = {
            "grant_type": "authorization_code",
            "code": auth_code,
            "redirect_uri": self.redirect_uri,
            "client_id": self.app_client_id,
            "client_secret": self.app_client_secret,
        }

        async with self.session.post(base_uri, data=data) as response:
            result = await response.json()

            if "errorCode" in result and result["errorCode"] is not None:
                error_msg = result.get("description", f"Ошибка {result['errorCode']}")
                raise ValueError(f"Ошибка получения токена: {error_msg}")

            if "access_token" not in result:
                raise ValueError("Отсутствует access_token в ответе сервера")

            return result

    async def refresh_token(
        self, refresh_token: str, base_uri: str = EndPoints.TOKEN_URI
    ) -> Dict[str, Any]:
        """Обновляет токен доступа.

        Args:
            refresh_token: Токен обновления
            base_uri: Базовый URI для обновления токена

        Returns:
            Словарь с новыми данными токена

        Raises:
            ValueError: При ошибке обновления токена
            RuntimeError: Если сессия не инициализирована
        """
        if not self.session:
            raise RuntimeError("Сессия не инициализирована. Используйте async with.")

        data = {
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
            "client_id": self.app_client_id,
            "client_secret": self.app_client_secret,
        }

        async with self.session.post(base_uri, data=data) as response:
            result = await response.json()

            if "errorCode" in result and result["errorCode"] is not None:
                error_msg = result.get("description", f"Ошибка {result['errorCode']}")
                raise ValueError(f"Ошибка обновления токена: {error_msg}")

            if "access_token" not in result:
                raise ValueError("Отсутствует access_token в ответе сервера")

            return result

    async def validate_token(self, access_token: str) -> bool:
        """Проверяет валидность токена доступа.

        Args:
            access_token: Токен доступа для проверки

        Returns:
            True если токен валиден, False иначе
        """
        # Простая проверка - токен должен быть непустой строкой
        # В реальной реализации можно добавить запрос к API для проверки
        return bool(
            access_token and isinstance(access_token, str) and len(access_token) > 10
        )
