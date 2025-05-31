"""Полный асинхронный коннектор для cTrader Open API на базе async/await."""

import asyncio
import json
import os
import aiohttp
import logging
import uuid
from typing import Optional, Dict, Any, List, Callable, Union
from datetime import datetime, timedelta
from urllib.parse import urlencode
from dataclasses import dataclass
from enum import Enum

# Импортируем нашу async библиотеку
from ctrader_open_api_async import AsyncClient, AsyncAuth, EndPoints, Protobuf

# Импортируем Protobuf сообщения
try:
    from ctrader_open_api_async.messages.OpenApiCommonMessages_pb2 import *
    from ctrader_open_api_async.messages.OpenApiMessages_pb2 import *
    from ctrader_open_api_async.messages.OpenApiModelMessages_pb2 import *
    from google.protobuf.json_format import MessageToJson
    PROTOBUF_AVAILABLE = True
except ImportError:
    PROTOBUF_AVAILABLE = False
    logging.warning("cTrader Protobuf библиотеки не найдены. Проверьте установку async библиотеки")

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class OrderType(Enum):
    """Типы ордеров."""
    MARKET = 1
    LIMIT = 2
    STOP = 3
    STOP_LIMIT = 4

class TradeSide(Enum):
    """Стороны торговли."""
    BUY = 1
    SELL = 2

class TrendbarPeriod(Enum):
    """Периоды трендбаров."""
    M1 = 1
    M2 = 2
    M3 = 3
    M4 = 4
    M5 = 5
    M10 = 10
    M15 = 15
    M30 = 30
    H1 = 60
    H4 = 240
    H12 = 720
    D1 = 1440
    W1 = 10080
    MN1 = 43200

class QuoteType(Enum):
    """Типы котировок."""
    BID = 1
    ASK = 2

@dataclass
class TokenData:
    """Данные токена авторизации."""
    access_token: str
    refresh_token: str
    expires_in: int
    issued_at: float
    token_type: str = "Bearer"

@dataclass
class AccountInfo:
    """Информация об аккаунте."""
    account_id: int
    broker_name: str
    account_type: str
    currency: str
    balance: float
    is_live: bool

@dataclass
class Symbol:
    """Информация о торговом символе."""
    symbol_id: int
    symbol_name: str
    base_asset: str
    quote_asset: str
    min_volume: float
    max_volume: float
    volume_step: float
    digits: int
    pip_position: int

@dataclass
class Position:
    """Информация о позиции."""
    position_id: int
    symbol_id: int
    symbol_name: str
    trade_side: TradeSide
    volume: float
    entry_price: float
    current_price: float
    unrealized_pnl: float
    swap: float
    commission: float
    margin_rate: float

@dataclass
class Order:
    """Информация об ордере."""
    order_id: int
    symbol_id: int
    symbol_name: str
    order_type: OrderType
    trade_side: TradeSide
    volume: float
    limit_price: Optional[float]
    stop_price: Optional[float]
    stop_loss: Optional[float]
    take_profit: Optional[float]
    label: Optional[str]
    comment: Optional[str]

@dataclass
class Deal:
    """Информация о сделке."""
    deal_id: int
    order_id: int
    position_id: int
    symbol_id: int
    volume: float
    price: float
    commission: float
    swap: float
    timestamp: int

@dataclass
class Trendbar:
    """Трендбар."""
    timestamp: int
    open_price: float
    high_price: float
    low_price: float
    close_price: float
    volume: int

@dataclass
class Tick:
    """Тик."""
    timestamp: int
    price: float
    volume: Optional[int] = None


class CTraderAsyncConnector:
    """Полный асинхронный коннектор для cTrader Open API."""
    
    def __init__(self, credentials_path: str, tokens_path: str = "tokens.json"):
        """Инициализация коннектора.

        Args:
            credentials_path: Путь к файлу с учетными данными.
            tokens_path: Путь к файлу для хранения токенов.
        """
        if not PROTOBUF_AVAILABLE:
            raise ImportError("Для работы с cTrader API необходимы Protobuf файлы в папке messages")
            
        self.credentials_path = credentials_path
        self.tokens_path = tokens_path
        self.client_id: Optional[str] = None
        self.client_secret: Optional[str] = None
        self.host_type: Optional[str] = None
        self.current_account_id: Optional[int] = None
        self.token: Optional[TokenData] = None
        
        # Клиенты
        self.client: Optional[AsyncClient] = None
        self.auth: Optional[AsyncAuth] = None
        self.session: Optional[aiohttp.ClientSession] = None
        
        # Данные
        self.symbols: Dict[int, Symbol] = {}
        self.positions: Dict[int, Position] = {}
        self.orders: Dict[int, Order] = {}
        self.accounts: List[AccountInfo] = []
        
        # Обработчики событий
        self.message_handlers: Dict[int, Callable] = {}
        
        # Загружаем данные при инициализации
        self.load_credentials()
        self.load_tokens()

    def load_credentials(self) -> None:
        """Загрузка учетных данных из файла."""
        try:
            with open(self.credentials_path, 'r') as f:
                creds = json.load(f)
                self.client_id = creds["clientId"]
                self.client_secret = creds["Secret"]
                self.host_type = creds["Host"].lower()
                logger.info("Учетные данные загружены")
        except Exception as e:
            logger.error(f"Ошибка загрузки учетных данных: {e}")
            raise

    def load_tokens(self) -> None:
        """Загрузка токенов из файла."""
        if os.path.exists(self.tokens_path):
            try:
                with open(self.tokens_path, 'r') as f:
                    token_dict = json.load(f)
                    
                    # Обрабатываем старый формат токенов
                    if "accessToken" in token_dict:
                        normalized_token = {
                            "access_token": token_dict.get("accessToken") or token_dict.get("access_token"),
                            "refresh_token": token_dict.get("refreshToken") or token_dict.get("refresh_token"),
                            "expires_in": token_dict.get("expiresIn") or token_dict.get("expires_in"),
                            "token_type": token_dict.get("tokenType", "Bearer"),
                            "issued_at": token_dict.get("issued_at", datetime.now().timestamp())
                        }
                        self.token = TokenData(**normalized_token)
                        self.save_tokens(self.token)
                    else:
                        self.token = TokenData(**token_dict)
                    
                    logger.info("Токены успешно загружены")
            except Exception as e:
                logger.error(f"Ошибка загрузки токенов: {e}")
                self.token = None

    def save_tokens(self, token_data: TokenData) -> None:
        """Сохранение токенов в файл."""
        try:
            with open(self.tokens_path, 'w') as f:
                json.dump(token_data.__dict__, f)
            logger.info("Токены сохранены")
        except Exception as e:
            logger.error(f"Ошибка сохранения токенов: {e}")

    async def __aenter__(self):
        """Асинхронный контекстный менеджер - вход."""
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Асинхронный контекстный менеджер - выход."""
        await self.disconnect()

    async def connect(self) -> None:
        """Подключение к cTrader API."""
        # Создаем HTTP сессию
        self.session = aiohttp.ClientSession()
        
        # Создаем auth клиент
        self.auth = AsyncAuth(
            self.client_id,
            self.client_secret,
            "http://localhost:8080/redirect"
        )
        self.auth.session = self.session
        
        # Проверяем и обновляем токен если нужно
        if self.token:
            await self.ensure_token_valid()
        
        # Создаем основной клиент
        if self.host_type == "live":
            self.client = AsyncClient.create_live_client()
        else:
            self.client = AsyncClient.create_demo_client()
        
        # Устанавливаем обработчики
        self.client.set_connected_callback(self._on_connected)
        self.client.set_disconnected_callback(self._on_disconnected)
        self.client.set_message_received_callback(self._handle_message)
        
        # Подключаемся
        await self.client.start_service()
        
        logger.info("Подключение к cTrader API установлено")

    async def disconnect(self) -> None:
        """Отключение от cTrader API."""
        if self.client:
            await self.client.stop_service()
            self.client = None
            
        if self.session:
            await self.session.close()
            self.session = None
            
        logger.info("Отключение от cTrader API")

    async def _on_connected(self, client: AsyncClient) -> None:
        """Обработчик подключения."""
        logger.info("Клиент подключен")
        # Автоматически авторизуем приложение
        await self.send_application_auth()

    async def _on_disconnected(self, client: AsyncClient, reason: str) -> None:
        """Обработчик отключения."""
        logger.info(f"Клиент отключен, причина: {reason}")

    async def _handle_message(self, client: Any, message: Any) -> None:
        """Обработка входящих сообщений."""
        try:
            # Получаем тип сообщения
            payload_type = message.payloadType
            
            # Обрабатываем различные типы сообщений
            if payload_type == ProtoOAPayloadType.PROTO_OA_ACCOUNT_AUTH_RES:
                logger.info("Аккаунт авторизован")
                
            elif payload_type == ProtoOAPayloadType.PROTO_OA_GET_ACCOUNTS_BY_ACCESS_TOKEN_RES:
                await self._handle_account_list_response(message)
                
            elif payload_type == ProtoOAPayloadType.PROTO_OA_SYMBOLS_LIST_RES:
                await self._handle_symbols_list_response(message)
                
            elif payload_type == ProtoOAPayloadType.PROTO_OA_SYMBOL_BY_ID_RES:
                await self._handle_symbol_by_id_response(message)
                
            elif payload_type == ProtoOAPayloadType.PROTO_OA_EXECUTION_EVENT:
                await self._handle_execution_event(message)
                
            elif payload_type == ProtoOAPayloadType.PROTO_OA_SPOT_EVENT:
                await self._handle_spot_event(message)
                
            # Вызываем пользовательские обработчики
            if payload_type in self.message_handlers:
                handler = self.message_handlers[payload_type]
                if asyncio.iscoroutinefunction(handler):
                    await handler(message)
                else:
                    handler(message)
                    
        except Exception as e:
            logger.error(f"Ошибка обработки сообщения: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")

    async def _handle_account_list_response(self, message: Any) -> None:
        """Обработка ответа со списком аккаунтов."""
        try:
            # Извлекаем данные из ProtoMessage
            from ctrader_open_api_async.protobuf import Protobuf
            extracted = Protobuf.extract(message)
            
            self.accounts.clear()
            
            # Проверяем наличие аккаунтов в ответе
            if hasattr(extracted, 'ctidTraderAccount') and extracted.ctidTraderAccount:
                for account in extracted.ctidTraderAccount:
                    account_info = AccountInfo(
                        account_id=account.ctidTraderAccountId,
                        broker_name="cTrader",
                        account_type="Demo" if not account.isLive else "Live",
                        currency="USD",  # По умолчанию
                        balance=0.0,
                        is_live=account.isLive
                    )
                    self.accounts.append(account_info)
                
                logger.info(f"Получено {len(self.accounts)} аккаунтов")
            else:
                logger.warning("В ответе отсутствуют аккаунты")
                logger.info(f"Доступные атрибуты в ответе: {dir(extracted)}")
                
        except Exception as e:
            logger.error(f"Ошибка обработки списка аккаунтов: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")

    async def _handle_symbols_list_response(self, message: Any) -> None:
        """Обработка ответа со списком символов."""
        try:
            # Извлекаем данные из ProtoMessage
            from ctrader_open_api_async.protobuf import Protobuf
            extracted = Protobuf.extract(message)
            
            self.symbols.clear()
            
            if hasattr(extracted, 'symbol') and extracted.symbol:
                for symbol in extracted.symbol:
                    symbol_info = Symbol(
                        symbol_id=getattr(symbol, 'symbolId', 0),
                        symbol_name=getattr(symbol, 'symbol_name', getattr(symbol, 'symbolName', 'Unknown')),
                        base_asset=getattr(symbol, 'baseAssetId', ''),
                        quote_asset=getattr(symbol, 'quoteAssetId', ''),
                        min_volume=getattr(symbol, 'minVolume', 0.01),
                        max_volume=getattr(symbol, 'maxVolume', 1000000),
                        volume_step=getattr(symbol, 'stepVolume', 0.01),
                        digits=getattr(symbol, 'digits', 5),
                        pip_position=getattr(symbol, 'pipPosition', 4)
                    )
                    self.symbols[symbol.symbolId] = symbol_info
                
                logger.info(f"Получено {len(self.symbols)} символов")
            else:
                logger.warning("В ответе отсутствуют символы")
                logger.info(f"Доступные атрибуты в ответе: {dir(extracted)}")
                
        except Exception as e:
            logger.error(f"Ошибка обработки списка символов: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")

    async def _handle_symbol_by_id_response(self, message: Any) -> None:
        """Обработка ответа с символом по ID."""
        try:
            # Извлекаем данные из ProtoMessage
            from ctrader_open_api_async.protobuf import Protobuf
            extracted = Protobuf.extract(message)
            
            # Ответ ProtoOASymbolByIdRes содержит массив символов
            if hasattr(extracted, 'symbol') and extracted.symbol:
                for symbol in extracted.symbol:
                    symbol_info = Symbol(
                        symbol_id=getattr(symbol, 'symbolId', 0),
                        symbol_name=getattr(symbol, 'symbol_name', getattr(symbol, 'symbolName', 'Unknown')),
                        base_asset=getattr(symbol, 'baseAssetId', ''),
                        quote_asset=getattr(symbol, 'quoteAssetId', ''),
                        min_volume=getattr(symbol, 'minVolume', 0.01),
                        max_volume=getattr(symbol, 'maxVolume', 1000000),
                        volume_step=getattr(symbol, 'stepVolume', 0.01),
                        digits=getattr(symbol, 'digits', 5),
                        pip_position=getattr(symbol, 'pipPosition', 4)
                    )
                    self.symbols[symbol.symbolId] = symbol_info
                    logger.info(f"Получен символ по ID: {symbol_info.symbol_name} (ID: {symbol_info.symbol_id})")
            else:
                logger.warning("В ответе отсутствуют символы")
                logger.info(f"Доступные атрибуты в ответе: {dir(extracted)}")
                
        except Exception as e:
            logger.error(f"Ошибка обработки символа по ID: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")

    async def _handle_execution_event(self, message: Any) -> None:
        """Обработка торговых событий."""
        try:
            # Извлекаем данные из ProtoMessage
            from ctrader_open_api_async.protobuf import Protobuf
            extracted = Protobuf.extract(message)
            
            if hasattr(extracted, 'executionType'):
                execution_type = extracted.executionType
                
                if execution_type == ProtoOAExecutionType.ORDER_FILLED:
                    if hasattr(extracted, 'order'):
                        order_info = extracted.order
                        is_closing = getattr(order_info, 'closingOrder', False)
                        if is_closing:
                            logger.info("🔴 ПОЗИЦИЯ ПОЛНОСТЬЮ ЗАКРЫТА!")
                        else:
                            logger.info("🟢 ПОЗИЦИЯ ОТКРЫТА!")
                            
                elif execution_type == ProtoOAExecutionType.ORDER_ACCEPTED:
                    if hasattr(extracted, 'order'):
                        order_info = extracted.order
                        is_closing = getattr(order_info, 'closingOrder', False)
                        if is_closing:
                            logger.info("⏳ Закрывающий ордер принят, ожидание исполнения...")
                        else:
                            logger.info("⏳ Открывающий ордер принят, ожидание исполнения...")
            else:
                logger.debug(f"Торговое событие без executionType: {dir(extracted)}")
                
        except Exception as e:
            logger.error(f"Ошибка обработки торгового события: {e}")

    async def _handle_spot_event(self, message: Any) -> None:
        """Обработка спотовых котировок."""
        try:
            # Извлекаем данные из ProtoMessage
            from ctrader_open_api_async.protobuf import Protobuf
            extracted = Protobuf.extract(message)
            
            if hasattr(extracted, 'symbolId'):
                symbol_id = extracted.symbolId
                if symbol_id in self.symbols:
                    symbol_name = self.symbols[symbol_id].symbol_name
                    bid = getattr(extracted, 'bid', None)
                    ask = getattr(extracted, 'ask', None)
                    logger.debug(f"Котировка {symbol_name}: bid={bid}, ask={ask}")
            else:
                logger.debug(f"Спотовое событие без symbolId: {dir(extracted)}")
                
        except Exception as e:
            logger.error(f"Ошибка обработки спотового события: {e}")

    # ========== МЕТОДЫ АВТОРИЗАЦИИ ==========
    
    def get_auth_uri(self) -> str:
        """Получение URL для авторизации."""
        return self.auth.get_auth_uri()

    async def get_token(self, auth_code: str) -> TokenData:
        """Получение токена по коду авторизации."""
        token_data = await self.auth.get_token(auth_code)
        token_data["issued_at"] = datetime.now().timestamp()
        
        self.token = TokenData(**token_data)
        self.save_tokens(self.token)
        logger.info("Токен успешно получен и сохранен")
        return self.token

    async def refresh_token(self) -> TokenData:
        """Обновление токена."""
        if not self.token or not self.token.refresh_token:
            raise ValueError("Отсутствует токен обновления")
            
        token_data = await self.auth.refresh_token(self.token.refresh_token)
        token_data["issued_at"] = datetime.now().timestamp()
        
        self.token = TokenData(**token_data)
        self.save_tokens(self.token)
        logger.info("Токен успешно обновлен")
        return self.token

    async def ensure_token_valid(self) -> None:
        """Проверка и обновление токена, если необходимо."""
        if not self.token:
            raise ValueError("Токен отсутствует, требуется авторизация")
            
        expires_at = datetime.fromtimestamp(self.token.expires_in + self.token.issued_at)
        if datetime.now() >= expires_at - timedelta(minutes=5):
            await self.refresh_token()

    # ========== БАЗОВЫЕ МЕТОДЫ API ==========
    
    async def send_application_auth(self) -> Any:
        """Отправка запроса на авторизацию приложения."""
        return await self.client.send_application_auth_req(
            self.client_id, 
            self.client_secret
        )

    async def send_version_req(self) -> Any:
        """Запрос версии API."""
        return await self.client.send_version_req()

    # ========== МЕТОДЫ РАБОТЫ С АККАУНТАМИ ==========
    
    async def get_account_list(self) -> List[AccountInfo]:
        """Получение списка аккаунтов."""
        response = await self.client.send_get_account_list_by_access_token_req(self.token.access_token)
        # Ждем пока аккаунты не будут обработаны
        await asyncio.sleep(0.5)
        return self.accounts

    async def set_account(self, account_id: int) -> None:
        """Установка текущего аккаунта."""
        self.current_account_id = account_id
        response = await self.client.send_account_auth_req(account_id, self.token.access_token)
        # Ждем подтверждения авторизации
        await asyncio.sleep(0.5)

    async def logout_account(self) -> None:
        """Выход из текущего аккаунта."""
        if self.current_account_id:
            await self.client.send_account_logout_req(self.current_account_id)
            self.current_account_id = None

    # ========== МЕТОДЫ РАБОТЫ С СИМВОЛАМИ ==========
    
    async def get_symbols(self, include_archived: bool = False) -> List[Symbol]:
        """Получение списка символов."""
        if not self.current_account_id:
            raise ValueError("Аккаунт не установлен. Сначала вызовите set_account()")
        
        # Увеличиваем таймаут для больших сообщений
        response = await self.client.send_symbols_list_req(
            self.current_account_id,
            include_archived
        )
        
        # Ждем обработки ответа
        await asyncio.sleep(2)
        
        return list(self.symbols.values())

    async def get_symbol_by_id(self, symbol_id: int) -> Optional[Symbol]:
        """Получение символа по ID."""
        response = await self.client.send_symbol_by_id_req(self.current_account_id, symbol_id)
        
        # Ждем обработки ответа
        await asyncio.sleep(0.5)
        
        # Возвращаем символ из кэша, если он был обновлен
        return self.symbols.get(symbol_id)

    async def get_assets(self) -> Any:
        """Получение списка активов."""
        if not self.current_account_id:
            raise ValueError("Аккаунт не установлен")
        return await self.client.send_asset_list_req(self.current_account_id)

    async def get_asset_classes(self) -> Any:
        """Получение списка классов активов."""
        if not self.current_account_id:
            raise ValueError("Аккаунт не установлен")
        return await self.client.send_asset_class_list_req(self.current_account_id)

    async def get_symbol_categories(self) -> Any:
        """Получение списка категорий символов."""
        if not self.current_account_id:
            raise ValueError("Аккаунт не установлен")
        return await self.client.send_symbol_category_list_req(self.current_account_id)

    # ========== МЕТОДЫ РАБОТЫ С КОТИРОВКАМИ ==========
    
    async def subscribe_spots(self, symbol_ids: List[int]) -> Any:
        """Подписка на спотовые котировки."""
        return await self.client.send_subscribe_spots_req(
            self.current_account_id, 
            symbol_ids
        )

    async def unsubscribe_spots(self, symbol_ids: List[int]) -> Any:
        """Отписка от спотовых котировок."""
        return await self.client.send_unsubscribe_spots_req(
            self.current_account_id, 
            symbol_ids
        )

    async def subscribe_live_trendbar(self, symbol_id: int, period: TrendbarPeriod) -> Any:
        """Подписка на живые трендбары."""
        return await self.client.send_subscribe_live_trendbar_req(
            self.current_account_id,
            period.value,
            symbol_id
        )

    async def unsubscribe_live_trendbar(self, symbol_id: int, period: TrendbarPeriod) -> Any:
        """Отписка от живых трендбаров."""
        return await self.client.send_unsubscribe_live_trendbar_req(
            self.current_account_id,
            period.value,
            symbol_id
        )

    # ========== МЕТОДЫ РАБОТЫ С ИСТОРИЧЕСКИМИ ДАННЫМИ ==========
    
    async def get_trendbars(self, 
                            symbol_id: int,
                            period: TrendbarPeriod,
                            from_timestamp: int,
                            to_timestamp: int,
                            count: Optional[int] = None) -> List[Trendbar]:
        """Получение исторических трендбаров."""
        response = await self.client.send_get_trendbars_req(
            self.current_account_id,
            from_timestamp,
            to_timestamp,
            period.value,
            symbol_id,
            count
        )
        
        # Парсим ответ и возвращаем список трендбаров
        extracted = Protobuf.extract(response)
        trendbars = []
        
        if hasattr(extracted, 'trendbar'):
            for tb in extracted.trendbar:
                # cTrader использует специальную структуру трендбаров
                # где цены представлены как дельты от базовой цены
                timestamp_minutes = getattr(tb, 'utcTimestampInMinutes', 0)
                timestamp = timestamp_minutes * 60 * 1000  # Конвертируем в миллисекунды
                
                # Получаем базовую цену (low) и дельты
                low_price = getattr(tb, 'low', 0) / 100000  # Конвертируем из центов
                delta_open = getattr(tb, 'deltaOpen', 0) / 100000
                delta_high = getattr(tb, 'deltaHigh', 0) / 100000
                delta_close = getattr(tb, 'deltaClose', 0) / 100000
                
                # Вычисляем цены
                open_price = low_price + delta_open
                high_price = low_price + delta_high
                close_price = low_price + delta_close
                
                trendbar = Trendbar(
                    timestamp=timestamp,
                    open_price=open_price,
                    high_price=high_price,
                    low_price=low_price,
                    close_price=close_price,
                    volume=getattr(tb, 'volume', 0)
                )
                trendbars.append(trendbar)
        
        return trendbars

    async def get_tick_data(self,
                            symbol_id: int,
                            quote_type: QuoteType,
                            from_timestamp: int,
                            to_timestamp: int) -> List[Tick]:
        """Получение тиковых данных."""
        response = await self.client.send_get_tick_data_req(
            self.current_account_id,
            from_timestamp,
            to_timestamp,
            symbol_id,
            quote_type.value
        )
        
        # Парсим ответ и возвращаем список тиков
        extracted = Protobuf.extract(response)
        ticks = []
        
        if hasattr(extracted, 'tickData'):
            for tick_data in extracted.tickData:
                tick = Tick(
                    timestamp=tick_data.timestamp,
                    price=tick_data.tick,
                    volume=getattr(tick_data, 'volume', None)
                )
                ticks.append(tick)
        
        return ticks

    # ========== ТОРГОВЫЕ МЕТОДЫ ==========
    
    async def place_market_order(self,
                                 symbol_id: int,
                                 trade_side: TradeSide,
                                 volume: int,
                                 stop_loss: Optional[float] = None,
                                 take_profit: Optional[float] = None,
                                 comment: Optional[str] = None,
                                 label: Optional[str] = None) -> Any:
        """Размещение рыночного ордера."""
        return await self.client.send_new_order_req(
            self.current_account_id,
            symbol_id,
            OrderType.MARKET.value,
            trade_side.value,
            volume,
            stop_loss=stop_loss,
            take_profit=take_profit,
            comment=comment,
            label=label
        )

    async def place_limit_order(self,
                                symbol_id: int,
                                trade_side: TradeSide,
                                volume: int,
                                limit_price: float,
                                stop_loss: Optional[float] = None,
                                take_profit: Optional[float] = None,
                                expiration_timestamp: Optional[int] = None,
                                comment: Optional[str] = None,
                                label: Optional[str] = None) -> Any:
        """Размещение лимитного ордера."""
        return await self.client.send_new_order_req(
            self.current_account_id,
            symbol_id,
            OrderType.LIMIT.value,
            trade_side.value,
            volume,
            limit_price=limit_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            expiration_timestamp=expiration_timestamp,
            comment=comment,
            label=label
        )

    async def place_stop_order(self,
                               symbol_id: int,
                               trade_side: TradeSide,
                               volume: int,
                               stop_price: float,
                               stop_loss: Optional[float] = None,
                               take_profit: Optional[float] = None,
                               expiration_timestamp: Optional[int] = None,
                               comment: Optional[str] = None,
                               label: Optional[str] = None) -> Any:
        """Размещение стоп ордера."""
        return await self.client.send_new_order_req(
            self.current_account_id,
            symbol_id,
            OrderType.STOP.value,
            trade_side.value,
            volume,
            stop_price=stop_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            expiration_timestamp=expiration_timestamp,
            comment=comment,
            label=label
        )

    async def cancel_order(self, order_id: int) -> Any:
        """Отмена ордера."""
        return await self.client.send_cancel_order_req(
            self.current_account_id,
            order_id
        )

    async def amend_order(self,
                          order_id: int,
                          volume: Optional[int] = None,
                          limit_price: Optional[float] = None,
                          stop_price: Optional[float] = None,
                          expiration_timestamp: Optional[int] = None,
                          stop_loss: Optional[float] = None,
                          take_profit: Optional[float] = None) -> Any:
        """Изменение ордера."""
        return await self.client.send_amend_order_req(
            self.current_account_id,
            order_id,
            volume=volume,
            limit_price=limit_price,
            stop_price=stop_price,
            expiration_timestamp=expiration_timestamp,
            stop_loss=stop_loss,
            take_profit=take_profit
        )

    async def close_position(self, position_id: int, volume: int) -> Any:
        """Закрытие позиции."""
        return await self.client.send_close_position_req(
            self.current_account_id,
            position_id,
            volume
        )

    async def amend_position_stop_loss(self, position_id: int, stop_loss: Optional[float] = None) -> Any:
        """Изменение стоп-лосса позиции."""
        return await self.client.send_amend_position_stop_loss_req(
            self.current_account_id,
            position_id,
            stop_loss
        )

    async def amend_position_take_profit(self, position_id: int, take_profit: Optional[float] = None) -> Any:
        """Изменение тейк-профита позиции."""
        return await self.client.send_amend_position_take_profit_req(
            self.current_account_id,
            position_id,
            take_profit
        )

    # ========== ИНФОРМАЦИОННЫЕ МЕТОДЫ ==========
    
    async def get_trader_info(self) -> Any:
        """Получение информации о трейдере."""
        if not self.current_account_id:
            raise ValueError("Аккаунт не установлен")
        if not self.client or not self.client.is_connected:
            raise ConnectionError("Соединение не установлено")
        return await self.client.send_trader_req(self.current_account_id)

    async def reconcile(self) -> Any:
        """Сверка позиций."""
        if not self.current_account_id:
            raise ValueError("Аккаунт не установлен")
        if not self.client or not self.client.is_connected:
            raise ConnectionError("Соединение не установлено")
        return await self.client.send_reconcile_req(self.current_account_id)

    async def get_order_details(self, order_id: int) -> Any:
        """Получение деталей ордера."""
        return await self.client.send_order_details_req(
            self.current_account_id,
            order_id
        )

    async def get_order_list(self,
                             from_timestamp: Optional[int] = None,
                             to_timestamp: Optional[int] = None) -> Any:
        """Получение списка ордеров."""
        if not self.current_account_id:
            raise ValueError("Аккаунт не установлен")
        if not self.client or not self.client.is_connected:
            raise ConnectionError("Соединение не установлено")
        
        # Если временные метки не указаны, используем последние 24 часа
        if from_timestamp is None:
            from_timestamp = int((datetime.now() - timedelta(days=1)).timestamp() * 1000)
        if to_timestamp is None:
            to_timestamp = int(datetime.now().timestamp() * 1000)
            
        return await self.client.send_order_list_req(
            self.current_account_id,
            from_timestamp,
            to_timestamp
        )

    async def get_deal_list(self,
                            from_timestamp: int,
                            to_timestamp: int,
                            max_rows: Optional[int] = None) -> Any:
        """Получение списка сделок."""
        if not self.current_account_id:
            raise ValueError("Аккаунт не установлен")
        if not self.client or not self.client.is_connected:
            raise ConnectionError("Соединение не установлено")
        return await self.client.send_deal_list_req(
            self.current_account_id,
            from_timestamp,
            to_timestamp,
            max_rows
        )

    async def get_position_unrealized_pnl(self) -> Any:
        """Получение нереализованной P&L."""
        if not self.current_account_id:
            raise ValueError("Аккаунт не установлен")
        if not self.client or not self.client.is_connected:
            raise ConnectionError("Соединение не установлено")
        return await self.client.send_get_position_unrealized_pnl_req(self.current_account_id)

    # ========== УДОБНЫЕ МЕТОДЫ ==========
    
    async def buy_market(self, symbol_id: int, volume: int, stop_loss: Optional[float] = None, take_profit: Optional[float] = None, comment: Optional[str] = None, label: Optional[str] = None) -> Any:
        """Покупка по рыночной цене."""
        return await self.place_market_order(symbol_id, TradeSide.BUY, volume, stop_loss, take_profit, comment, label)

    async def sell_market(self, symbol_id: int, volume: int, stop_loss: Optional[float] = None, take_profit: Optional[float] = None, comment: Optional[str] = None, label: Optional[str] = None) -> Any:
        """Продажа по рыночной цене."""
        return await self.place_market_order(symbol_id, TradeSide.SELL, volume, stop_loss, take_profit, comment, label)

    def add_message_handler(self, payload_type: int, handler: Callable) -> None:
        """Добавление обработчика сообщений."""
        self.message_handlers[payload_type] = handler

    def remove_message_handler(self, payload_type: int) -> None:
        """Удаление обработчика сообщений."""
        self.message_handlers.pop(payload_type, None)

    def get_symbol_by_name(self, symbol_name: str) -> Optional[Symbol]:
        """Получение символа по имени."""
        for symbol in self.symbols.values():
            if symbol.symbol_name == symbol_name:
                return symbol
        return None 