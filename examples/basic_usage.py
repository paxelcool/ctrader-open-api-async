#!/usr/bin/env python3
"""
Базовый пример использования cTrader Open API Async.

⚠️ ВНИМАНИЕ: Этот пример устарел и не учитывает OAuth авторизацию!

Для правильной реализации OAuth авторизации используйте:
- oauth_auth_example.py - полный автоматический пример
- simple_oauth_example.py - упрощенный пример с ручным вводом

Подробнее: https://help.ctrader.com/open-api/account-authentication/
"""

import asyncio
import logging
from typing import Optional

from ctrader_open_api_async import AsyncClient, EndPoints
from ctrader_open_api_async.messages.OpenApiCommonMessages_pb2 import *
from ctrader_open_api_async.messages.OpenApiMessages_pb2 import *

# Настройка логирования
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class CTraderExample:
    """
    Пример класса для работы с cTrader API.
    
    ⚠️ УСТАРЕВШИЙ - не поддерживает OAuth авторизацию!
    """

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        access_token: str,
        is_live: bool = False,
    ):
        """Инициализация примера.

        Args:
            client_id: ID приложения
            client_secret: Секрет приложения  
            access_token: Токен доступа (должен быть получен через OAuth!)
            is_live: Использовать live сервер (по умолчанию demo)
        """
        self.client_id = client_id
        self.client_secret = client_secret
        self.access_token = access_token

        # Выбор хоста
        host = EndPoints.PROTOBUF_LIVE_HOST if is_live else EndPoints.PROTOBUF_DEMO_HOST
        self.client = AsyncClient(host, EndPoints.PROTOBUF_PORT)

        self.account_id: Optional[int] = None

    async def connect_and_auth(self) -> bool:
        """Подключение и аутентификация.

        Returns:
            True если успешно, False иначе
        """
        try:
            # Подключение
            await self.client.start_service()
            logger.info("Подключено к cTrader Open API")

            # Аутентификация приложения
            auth_response = await self.client.send_application_auth_req(
                self.client_id, self.client_secret
            )
            logger.info("Аутентификация приложения успешна")

            return True

        except Exception as e:
            logger.error(f"Ошибка подключения/аутентификации: {e}")
            return False

    async def get_accounts(self) -> list:
        """Получение списка аккаунтов.

        Returns:
            Список аккаунтов
        """
        try:
            response = await self.client.send_get_account_list_by_access_token_req(
                self.access_token
            )
            accounts = list(response.ctidTraderAccount)

            if accounts:
                self.account_id = accounts[0].ctidTraderAccountId
                logger.info(f"Найдено аккаунтов: {len(accounts)}")
                logger.info(f"Используется аккаунт ID: {self.account_id}")

                # Авторизация торгового аккаунта
                await self.client.send_account_auth_req(
                    self.account_id, self.access_token
                )
                logger.info("Авторизация торгового аккаунта успешна")

            return accounts

        except Exception as e:
            logger.error(f"Ошибка получения аккаунтов: {e}")
            return []

    async def get_symbols(self) -> list:
        """Получение списка символов.

        Returns:
            Список символов
        """
        if not self.account_id:
            logger.error("Аккаунт не выбран")
            return []

        try:
            response = await self.client.send_symbols_list_req(self.account_id)
            symbols = list(response.symbol)

            logger.info(f"Найдено символов: {len(symbols)}")

            # Показываем первые 5 символов
            for i, symbol in enumerate(symbols[:5]):
                logger.info(
                    f"Символ {i+1}: {symbol.symbolName} (ID: {symbol.symbolId})"
                )

            return symbols

        except Exception as e:
            logger.error(f"Ошибка получения символов: {e}")
            return []

    async def subscribe_to_spots(self, symbol_ids: list) -> None:
        """Подписка на спот цены.

        Args:
            symbol_ids: Список ID символов
        """
        if not self.account_id:
            logger.error("Аккаунт не выбран")
            return

        try:
            await self.client.send_subscribe_spots_req(self.account_id, symbol_ids)
            logger.info(f"Подписка на спот цены для символов: {symbol_ids}")

        except Exception as e:
            logger.error(f"Ошибка подписки на спот цены: {e}")

    async def listen_for_spots(self, duration: int = 30) -> None:
        """Прослушивание спот цен.

        Args:
            duration: Длительность прослушивания в секундах
        """
        logger.info(f"Прослушивание спот цен в течение {duration} секунд...")

        # Установка обработчика сообщений
        def on_message(client, message):
            if hasattr(message, 'payloadType') and hasattr(message, 'payload'):
                # Простая проверка типа сообщения (без полного парсинга)
                logger.info(f"Получено сообщение типа: {message.payloadType}")

        self.client.set_message_received_callback(on_message)

        # Ожидание в течение указанного времени
        await asyncio.sleep(duration)

    async def disconnect(self) -> None:
        """Отключение от API."""
        try:
            if self.account_id:
                await self.client.send_account_logout_req(self.account_id)
                logger.info("Выход из торгового аккаунта")

            await self.client.stop_service()
            logger.info("Отключено от cTrader Open API")
        except Exception as e:
            logger.error(f"Ошибка отключения: {e}")


async def main():
    """Основная функция примера."""
    
    print("=" * 80)
    print("⚠️  ВНИМАНИЕ: УСТАРЕВШИЙ ПРИМЕР!")
    print("=" * 80)
    print("Этот пример НЕ реализует правильную OAuth авторизацию!")
    print("Согласно документации cTrader API, необходимо использовать OAuth 2.0 поток.")
    print("")
    print("📋 Для правильной реализации используйте:")
    print("   • oauth_auth_example.py - полный автоматический пример")
    print("   • simple_oauth_example.py - упрощенный пример")
    print("")
    print("📖 Документация: https://help.ctrader.com/open-api/account-authentication/")
    print("=" * 80)
    
    # Ждем подтверждение от пользователя
    user_input = input("\nПродолжить выполнение устаревшего примера? (y/N): ").strip().lower()
    if user_input not in ['y', 'yes', 'да']:
        print("Используйте oauth_auth_example.py для правильной авторизации!")
        return

    # ВАЖНО: Замените эти значения на ваши реальные данные
    CLIENT_ID = "your_client_id"
    CLIENT_SECRET = "your_client_secret"
    ACCESS_TOKEN = "your_access_token"  # Должен быть получен через OAuth!
    IS_LIVE = False  # True для live сервера, False для demo

    if CLIENT_ID == "your_client_id":
        logger.error(
            "Пожалуйста, укажите ваши реальные CLIENT_ID, CLIENT_SECRET и ACCESS_TOKEN"
        )
        logger.error("ACCESS_TOKEN должен быть получен через OAuth авторизацию!")
        return

    example = CTraderExample(CLIENT_ID, CLIENT_SECRET, ACCESS_TOKEN, IS_LIVE)

    try:
        # Подключение и аутентификация
        if not await example.connect_and_auth():
            return

        # Получение аккаунтов
        accounts = await example.get_accounts()
        if not accounts:
            logger.error("Не найдено аккаунтов")
            return

        # Получение символов
        symbols = await example.get_symbols()
        if not symbols:
            logger.error("Не найдено символов")
            return

        # Подписка на первые 3 символа
        symbol_ids = [symbol.symbolId for symbol in symbols[:3]]
        await example.subscribe_to_spots(symbol_ids)

        # Прослушивание спот цен
        await example.listen_for_spots(30)

    except KeyboardInterrupt:
        logger.info("Прервано пользователем")
    except Exception as e:
        logger.error(f"Неожиданная ошибка: {e}")
    finally:
        await example.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
