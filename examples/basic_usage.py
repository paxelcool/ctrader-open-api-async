#!/usr/bin/env python3
"""Базовый пример использования cTrader Open API Async."""

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
    """Пример класса для работы с cTrader API."""

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
            access_token: Токен доступа
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
            await self.client.connect()
            logger.info("Подключено к cTrader Open API")

            # Аутентификация приложения
            auth_request = ProtoOAApplicationAuthReq()
            auth_request.clientId = self.client_id
            auth_request.clientSecret = self.client_secret

            auth_response = await self.client.send_request(auth_request)
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
            request = ProtoOAGetAccountListByAccessTokenReq()
            request.accessToken = self.access_token

            response = await self.client.send_request(request)
            accounts = list(response.ctidTraderAccount)

            if accounts:
                self.account_id = accounts[0].ctidTraderAccountId
                logger.info(f"Найдено аккаунтов: {len(accounts)}")
                logger.info(f"Используется аккаунт ID: {self.account_id}")

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
            request = ProtoOASymbolsListReq()
            request.ctidTraderAccountId = self.account_id

            response = await self.client.send_request(request)
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
            request = ProtoOASubscribeSpotsReq()
            request.ctidTraderAccountId = self.account_id
            request.symbolId.extend(symbol_ids)

            await self.client.send_request(request)
            logger.info(f"Подписка на спот цены для символов: {symbol_ids}")

        except Exception as e:
            logger.error(f"Ошибка подписки на спот цены: {e}")

    async def listen_for_spots(self, duration: int = 30) -> None:
        """Прослушивание спот цен.

        Args:
            duration: Длительность прослушивания в секундах
        """
        logger.info(f"Прослушивание спот цен в течение {duration} секунд...")

        end_time = asyncio.get_event_loop().time() + duration

        try:
            async for message in self.client.message_stream():
                if asyncio.get_event_loop().time() > end_time:
                    break

                if message.payloadType == ProtoOAPayloadType.PROTO_OA_SPOT_EVENT:
                    spot_event = ProtoOASpotEvent()
                    spot_event.ParseFromString(message.payload)

                    logger.info(
                        f"Спот цена - Символ ID: {spot_event.symbolId}, "
                        f"Bid: {spot_event.bid}, Ask: {spot_event.ask}"
                    )

        except Exception as e:
            logger.error(f"Ошибка при прослушивании спот цен: {e}")

    async def disconnect(self) -> None:
        """Отключение от API."""
        try:
            await self.client.disconnect()
            logger.info("Отключено от cTrader Open API")
        except Exception as e:
            logger.error(f"Ошибка отключения: {e}")


async def main():
    """Основная функция примера."""
    # ВАЖНО: Замените эти значения на ваши реальные данные
    CLIENT_ID = "your_client_id"
    CLIENT_SECRET = "your_client_secret"
    ACCESS_TOKEN = "your_access_token"
    IS_LIVE = False  # True для live сервера, False для demo

    if CLIENT_ID == "your_client_id":
        logger.error(
            "Пожалуйста, укажите ваши реальные CLIENT_ID, CLIENT_SECRET и ACCESS_TOKEN"
        )
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
