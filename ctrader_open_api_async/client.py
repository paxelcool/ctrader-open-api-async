"""Асинхронный клиент для cTrader Open API."""

import asyncio
import uuid
import logging
from typing import Optional, Dict, Any, Callable, Union
from datetime import datetime, timedelta

from .tcp_protocol import AsyncTcpProtocol
from .protobuf import Protobuf
from .endpoints import EndPoints

# Импортируем все необходимые Protobuf сообщения
try:
    from .messages.OpenApiCommonMessages_pb2 import ProtoMessage, ProtoHeartbeatEvent
    from .messages.OpenApiMessages_pb2 import *
    from .messages.OpenApiModelMessages_pb2 import *
    PROTOBUF_AVAILABLE = True
except ImportError:
    PROTOBUF_AVAILABLE = False

logger = logging.getLogger(__name__)


class AsyncClient:
    """Асинхронный клиент для cTrader Open API."""
    
    def __init__(self, 
                 host: str, 
                 port: int, 
                 messages_per_second: int = 5,
                 response_timeout: float = 30.0):
        """Инициализация клиента.
        
        Args:
            host: Хост сервера cTrader
            port: Порт сервера cTrader
            messages_per_second: Количество сообщений в секунду
            response_timeout: Таймаут ожидания ответа в секундах
        """
        if not PROTOBUF_AVAILABLE:
            raise ImportError("Для работы требуется библиотека ctrader-open-api")
            
        self.host = host
        self.port = port
        self.messages_per_second = messages_per_second
        self.response_timeout = response_timeout
        
        # TCP протокол
        self.protocol: Optional[AsyncTcpProtocol] = None
        self.is_connected = False
        
        # Обработчики событий
        self._connected_callback: Optional[Callable] = None
        self._disconnected_callback: Optional[Callable] = None
        self._message_received_callback: Optional[Callable] = None
        
        # Ожидающие ответы
        self._response_futures: Dict[str, asyncio.Future] = {}
        
        # Состояние
        self._running = False

    async def start_service(self) -> None:
        """Запускает сервис клиента."""
        if self._running:
            return
            
        self._running = True
        
        # Создаем TCP протокол
        self.protocol = AsyncTcpProtocol(
            self.host, 
            self.port, 
            messages_per_second=self.messages_per_second
        )
        
        # Устанавливаем обработчики
        self.protocol.set_connected_callback(self._on_connected)
        self.protocol.set_disconnected_callback(self._on_disconnected)
        self.protocol.set_message_received_callback(self._on_message_received)
        
        # Подключаемся
        await self.protocol.connect()

    async def stop_service(self) -> None:
        """Останавливает сервис клиента."""
        if not self._running:
            return
            
        self._running = False
        
        # Отменяем все ожидающие ответы
        for future in self._response_futures.values():
            if not future.done():
                future.cancel()
        self._response_futures.clear()
        
        # Отключаемся
        if self.protocol:
            await self.protocol.disconnect()
            self.protocol = None

    async def _on_connected(self) -> None:
        """Обработчик подключения."""
        self.is_connected = True
        if self._connected_callback:
            if asyncio.iscoroutinefunction(self._connected_callback):
                await self._connected_callback(self)
            else:
                self._connected_callback(self)

    async def _on_disconnected(self, reason: str) -> None:
        """Обработчик отключения."""
        self.is_connected = False
        
        # Отменяем все ожидающие ответы
        for future in self._response_futures.values():
            if not future.done():
                future.set_exception(ConnectionError(f"Соединение потеряно: {reason}"))
        self._response_futures.clear()
        
        if self._disconnected_callback:
            if asyncio.iscoroutinefunction(self._disconnected_callback):
                await self._disconnected_callback(self, reason)
            else:
                self._disconnected_callback(self, reason)

    async def _on_message_received(self, message: ProtoMessage) -> None:
        """Обработчик получения сообщений."""
        # Вызываем пользовательский обработчик
        if self._message_received_callback:
            if asyncio.iscoroutinefunction(self._message_received_callback):
                await self._message_received_callback(self, message)
            else:
                self._message_received_callback(self, message)
        
        # Обрабатываем ответы на запросы
        if message.clientMsgId and message.clientMsgId in self._response_futures:
            future = self._response_futures.pop(message.clientMsgId)
            if not future.done():
                future.set_result(message)

    async def send(self, 
                   message: Any, 
                   client_msg_id: Optional[str] = None, 
                   response_timeout: Optional[float] = None,
                   **params) -> ProtoMessage:
        """Отправляет сообщение и ждет ответ.
        
        Args:
            message: Сообщение для отправки (может быть типом, строкой или объектом)
            client_msg_id: ID клиентского сообщения
            response_timeout: Таймаут ожидания ответа
            **params: Дополнительные параметры для создания сообщения
            
        Returns:
            Ответное сообщение
            
        Raises:
            ConnectionError: Если нет соединения
            asyncio.TimeoutError: При таймауте ожидания ответа
        """
        if not self.is_connected or not self.protocol:
            raise ConnectionError("Клиент не подключен")
        
        # Создаем сообщение если передан тип или строка
        if isinstance(message, (str, int)):
            message = Protobuf.get(message, **params)
        
        # Генерируем ID сообщения если не указан
        if client_msg_id is None:
            client_msg_id = str(uuid.uuid4())
        
        # Создаем Future для ожидания ответа
        response_future = asyncio.Future()
        self._response_futures[client_msg_id] = response_future
        
        try:
            # Отправляем сообщение
            await self.protocol.send(message, client_msg_id=client_msg_id)
            
            # Ждем ответ с таймаутом
            timeout = response_timeout or self.response_timeout
            response = await asyncio.wait_for(response_future, timeout=timeout)
            
            return response
            
        except asyncio.TimeoutError:
            # Удаляем из ожидающих при таймауте
            self._response_futures.pop(client_msg_id, None)
            raise
        except Exception:
            # Удаляем из ожидающих при ошибке
            self._response_futures.pop(client_msg_id, None)
            raise

    def set_connected_callback(self, callback: Callable) -> None:
        """Устанавливает обработчик подключения."""
        self._connected_callback = callback

    def set_disconnected_callback(self, callback: Callable) -> None:
        """Устанавливает обработчик отключения."""
        self._disconnected_callback = callback

    def set_message_received_callback(self, callback: Callable) -> None:
        """Устанавливает обработчик получения сообщений."""
        self._message_received_callback = callback

    # Контекстный менеджер
    async def __aenter__(self):
        """Асинхронный контекстный менеджер - вход."""
        await self.start_service()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Асинхронный контекстный менеджер - выход."""
        await self.stop_service()

    # ========== API МЕТОДЫ ==========
    
    # Базовые методы
    async def send_application_auth_req(self, 
                                        client_id: str, 
                                        client_secret: str,
                                        client_msg_id: Optional[str] = None) -> ProtoMessage:
        """Авторизация приложения."""
        request = ProtoOAApplicationAuthReq()
        request.clientId = client_id
        request.clientSecret = client_secret
        return await self.send(request, client_msg_id)

    async def send_version_req(self, client_msg_id: Optional[str] = None) -> ProtoMessage:
        """Запрос версии API."""
        request = ProtoOAVersionReq()
        return await self.send(request, client_msg_id)

    # Методы работы с аккаунтами
    async def send_get_account_list_by_access_token_req(self, 
                                                        access_token: str,
                                                        client_msg_id: Optional[str] = None) -> ProtoMessage:
        """Получение списка аккаунтов по токену доступа."""
        request = ProtoOAGetAccountListByAccessTokenReq()
        request.accessToken = access_token
        return await self.send(request, client_msg_id)

    async def send_account_auth_req(self, 
                                    ctid_trader_account_id: int, 
                                    access_token: str,
                                    client_msg_id: Optional[str] = None) -> ProtoMessage:
        """Авторизация торгового аккаунта."""
        request = ProtoOAAccountAuthReq()
        request.ctidTraderAccountId = ctid_trader_account_id
        request.accessToken = access_token
        return await self.send(request, client_msg_id)

    async def send_account_logout_req(self, 
                                      ctid_trader_account_id: int,
                                      client_msg_id: Optional[str] = None) -> ProtoMessage:
        """Выход из торгового аккаунта."""
        request = ProtoOAAccountLogoutReq()
        request.ctidTraderAccountId = ctid_trader_account_id
        return await self.send(request, client_msg_id)

    # Методы работы с активами и символами
    async def send_asset_list_req(self, 
                                  ctid_trader_account_id: int,
                                  client_msg_id: Optional[str] = None) -> ProtoMessage:
        """Получение списка активов."""
        request = ProtoOAAssetListReq()
        request.ctidTraderAccountId = ctid_trader_account_id
        return await self.send(request, client_msg_id)

    async def send_asset_class_list_req(self, 
                                        ctid_trader_account_id: int,
                                        client_msg_id: Optional[str] = None) -> ProtoMessage:
        """Получение списка классов активов."""
        request = ProtoOAAssetClassListReq()
        request.ctidTraderAccountId = ctid_trader_account_id
        return await self.send(request, client_msg_id)

    async def send_symbol_category_list_req(self, 
                                            ctid_trader_account_id: int,
                                            client_msg_id: Optional[str] = None) -> ProtoMessage:
        """Получение списка категорий символов."""
        request = ProtoOASymbolCategoryListReq()
        request.ctidTraderAccountId = ctid_trader_account_id
        return await self.send(request, client_msg_id)

    async def send_symbols_list_req(self, 
                                    ctid_trader_account_id: int,
                                    include_archived: bool = False,
                                    client_msg_id: Optional[str] = None) -> ProtoMessage:
        """Получение списка символов."""
        request = ProtoOASymbolsListReq()
        request.ctidTraderAccountId = ctid_trader_account_id
        request.includeArchivedSymbols = include_archived
        return await self.send(request, client_msg_id)

    async def send_symbol_by_id_req(self, 
                                    ctid_trader_account_id: int,
                                    symbol_id: int,
                                    client_msg_id: Optional[str] = None) -> ProtoMessage:
        """Получение символа по ID."""
        request = ProtoOASymbolByIdReq()
        request.ctidTraderAccountId = ctid_trader_account_id
        request.symbolId.append(symbol_id)  # symbolId является repeated полем
        return await self.send(request, client_msg_id)

    # Методы работы с котировками
    async def send_subscribe_spots_req(self, 
                                       ctid_trader_account_id: int,
                                       symbol_ids: list,
                                       client_msg_id: Optional[str] = None) -> ProtoMessage:
        """Подписка на спотовые котировки."""
        request = ProtoOASubscribeSpotsReq()
        request.ctidTraderAccountId = ctid_trader_account_id
        request.symbolId.extend(symbol_ids)
        return await self.send(request, client_msg_id)

    async def send_unsubscribe_spots_req(self, 
                                         ctid_trader_account_id: int,
                                         symbol_ids: list,
                                         client_msg_id: Optional[str] = None) -> ProtoMessage:
        """Отписка от спотовых котировок."""
        request = ProtoOAUnsubscribeSpotsReq()
        request.ctidTraderAccountId = ctid_trader_account_id
        request.symbolId.extend(symbol_ids)
        return await self.send(request, client_msg_id)

    async def send_subscribe_live_trendbar_req(self, 
                                               ctid_trader_account_id: int,
                                               period: int,
                                               symbol_id: int,
                                               client_msg_id: Optional[str] = None) -> ProtoMessage:
        """Подписка на живые трендбары."""
        request = ProtoOASubscribeLiveTrendbarReq()
        request.ctidTraderAccountId = ctid_trader_account_id
        request.period = period
        request.symbolId = symbol_id
        return await self.send(request, client_msg_id)

    async def send_unsubscribe_live_trendbar_req(self, 
                                                 ctid_trader_account_id: int,
                                                 period: int,
                                                 symbol_id: int,
                                                 client_msg_id: Optional[str] = None) -> ProtoMessage:
        """Отписка от живых трендбаров."""
        request = ProtoOAUnsubscribeLiveTrendbarReq()
        request.ctidTraderAccountId = ctid_trader_account_id
        request.period = period
        request.symbolId = symbol_id
        return await self.send(request, client_msg_id)

    # Методы работы с историческими данными
    async def send_get_trendbars_req(self, 
                                     ctid_trader_account_id: int,
                                     from_timestamp: int,
                                     to_timestamp: int,
                                     period: int,
                                     symbol_id: int,
                                     count: Optional[int] = None,
                                     client_msg_id: Optional[str] = None) -> ProtoMessage:
        """Получение исторических трендбаров."""
        request = ProtoOAGetTrendbarsReq()
        request.ctidTraderAccountId = ctid_trader_account_id
        request.fromTimestamp = from_timestamp
        request.toTimestamp = to_timestamp
        request.period = period
        request.symbolId = symbol_id
        if count is not None:
            request.count = count
        return await self.send(request, client_msg_id)

    async def send_get_tick_data_req(self, 
                                     ctid_trader_account_id: int,
                                     from_timestamp: int,
                                     to_timestamp: int,
                                     symbol_id: int,
                                     quote_type: int,
                                     client_msg_id: Optional[str] = None) -> ProtoMessage:
        """Получение тиковых данных."""
        request = ProtoOAGetTickDataReq()
        request.ctidTraderAccountId = ctid_trader_account_id
        request.fromTimestamp = from_timestamp
        request.toTimestamp = to_timestamp
        request.symbolId = symbol_id
        request.type = quote_type
        return await self.send(request, client_msg_id)

    # Торговые методы
    async def send_new_order_req(self, 
                                 ctid_trader_account_id: int,
                                 symbol_id: int,
                                 order_type: int,
                                 trade_side: int,
                                 volume: int,
                                 limit_price: Optional[float] = None,
                                 stop_price: Optional[float] = None,
                                 stop_loss: Optional[float] = None,
                                 take_profit: Optional[float] = None,
                                 expiration_timestamp: Optional[int] = None,
                                 stop_trigger_method: Optional[int] = None,
                                 comment: Optional[str] = None,
                                 label: Optional[str] = None,
                                 client_msg_id: Optional[str] = None) -> ProtoMessage:
        """Создание нового ордера."""
        request = ProtoOANewOrderReq()
        request.ctidTraderAccountId = ctid_trader_account_id
        request.symbolId = symbol_id
        request.orderType = order_type
        request.tradeSide = trade_side
        request.volume = volume
        
        if limit_price is not None:
            request.limitPrice = limit_price
        if stop_price is not None:
            request.stopPrice = stop_price
        if stop_loss is not None:
            request.stopLoss = stop_loss
        if take_profit is not None:
            request.takeProfit = take_profit
        if expiration_timestamp is not None:
            request.expirationTimestamp = expiration_timestamp
        if stop_trigger_method is not None:
            request.stopTriggerMethod = stop_trigger_method
        if comment is not None:
            request.comment = comment
        if label is not None:
            request.label = label
            
        return await self.send(request, client_msg_id)

    async def send_cancel_order_req(self, 
                                    ctid_trader_account_id: int,
                                    order_id: int,
                                    client_msg_id: Optional[str] = None) -> ProtoMessage:
        """Отмена ордера."""
        request = ProtoOACancelOrderReq()
        request.ctidTraderAccountId = ctid_trader_account_id
        request.orderId = order_id
        return await self.send(request, client_msg_id)

    async def send_amend_order_req(self, 
                                   ctid_trader_account_id: int,
                                   order_id: int,
                                   volume: Optional[int] = None,
                                   limit_price: Optional[float] = None,
                                   stop_price: Optional[float] = None,
                                   expiration_timestamp: Optional[int] = None,
                                   stop_loss: Optional[float] = None,
                                   take_profit: Optional[float] = None,
                                   stop_trigger_method: Optional[int] = None,
                                   client_msg_id: Optional[str] = None) -> ProtoMessage:
        """Изменение ордера."""
        request = ProtoOAAmendOrderReq()
        request.ctidTraderAccountId = ctid_trader_account_id
        request.orderId = order_id
        
        if volume is not None:
            request.volume = volume
        if limit_price is not None:
            request.limitPrice = limit_price
        if stop_price is not None:
            request.stopPrice = stop_price
        if expiration_timestamp is not None:
            request.expirationTimestamp = expiration_timestamp
        if stop_loss is not None:
            request.stopLoss = stop_loss
        if take_profit is not None:
            request.takeProfit = take_profit
        if stop_trigger_method is not None:
            request.stopTriggerMethod = stop_trigger_method
            
        return await self.send(request, client_msg_id)

    async def send_close_position_req(self, 
                                      ctid_trader_account_id: int,
                                      position_id: int,
                                      volume: int,
                                      client_msg_id: Optional[str] = None) -> ProtoMessage:
        """Закрытие позиции."""
        request = ProtoOAClosePositionReq()
        request.ctidTraderAccountId = ctid_trader_account_id
        request.positionId = position_id
        request.volume = volume
        return await self.send(request, client_msg_id)

    async def send_amend_position_stop_loss_req(self, 
                                                ctid_trader_account_id: int,
                                                position_id: int,
                                                stop_loss: Optional[float] = None,
                                                client_msg_id: Optional[str] = None) -> ProtoMessage:
        """Изменение стоп-лосса позиции."""
        request = ProtoOAAmendPositionStopLossReq()
        request.ctidTraderAccountId = ctid_trader_account_id
        request.positionId = position_id
        if stop_loss is not None:
            request.stopLoss = stop_loss
        return await self.send(request, client_msg_id)

    async def send_amend_position_take_profit_req(self, 
                                                  ctid_trader_account_id: int,
                                                  position_id: int,
                                                  take_profit: Optional[float] = None,
                                                  client_msg_id: Optional[str] = None) -> ProtoMessage:
        """Изменение тейк-профита позиции."""
        request = ProtoOAAmendPositionTakeProfitReq()
        request.ctidTraderAccountId = ctid_trader_account_id
        request.positionId = position_id
        if take_profit is not None:
            request.takeProfit = take_profit
        return await self.send(request, client_msg_id)

    # Информационные методы
    async def send_trader_req(self, 
                              ctid_trader_account_id: int,
                              client_msg_id: Optional[str] = None) -> ProtoMessage:
        """Получение информации о трейдере."""
        request = ProtoOATraderReq()
        request.ctidTraderAccountId = ctid_trader_account_id
        return await self.send(request, client_msg_id)

    async def send_reconcile_req(self, 
                                 ctid_trader_account_id: int,
                                 client_msg_id: Optional[str] = None) -> ProtoMessage:
        """Сверка позиций и ордеров."""
        request = ProtoOAReconcileReq()
        request.ctidTraderAccountId = ctid_trader_account_id
        return await self.send(request, client_msg_id)

    async def send_order_details_req(self, 
                                     ctid_trader_account_id: int,
                                     order_id: int,
                                     client_msg_id: Optional[str] = None) -> ProtoMessage:
        """Получение деталей ордера."""
        request = ProtoOAOrderDetailsReq()
        request.ctidTraderAccountId = ctid_trader_account_id
        request.orderId = order_id
        return await self.send(request, client_msg_id)

    async def send_order_list_req(self, 
                                  ctid_trader_account_id: int,
                                  from_timestamp: Optional[int] = None,
                                  to_timestamp: Optional[int] = None,
                                  client_msg_id: Optional[str] = None) -> ProtoMessage:
        """Получение списка ордеров."""
        request = ProtoOAOrderListReq()
        request.ctidTraderAccountId = ctid_trader_account_id
        if from_timestamp is not None:
            request.fromTimestamp = from_timestamp
        if to_timestamp is not None:
            request.toTimestamp = to_timestamp
        return await self.send(request, client_msg_id)

    async def send_deal_list_req(self, 
                                 ctid_trader_account_id: int,
                                 from_timestamp: int,
                                 to_timestamp: int,
                                 max_rows: Optional[int] = None,
                                 client_msg_id: Optional[str] = None) -> ProtoMessage:
        """Получение списка сделок."""
        request = ProtoOADealListReq()
        request.ctidTraderAccountId = ctid_trader_account_id
        request.fromTimestamp = from_timestamp
        request.toTimestamp = to_timestamp
        if max_rows is not None:
            request.maxRows = max_rows
        return await self.send(request, client_msg_id)

    async def send_get_position_unrealized_pnl_req(self, 
                                                   ctid_trader_account_id: int,
                                                   client_msg_id: Optional[str] = None) -> ProtoMessage:
        """Получение нереализованной прибыли/убытка."""
        request = ProtoOAGetPositionUnrealizedPnLReq()
        request.ctidTraderAccountId = ctid_trader_account_id
        return await self.send(request, client_msg_id)

    # Дополнительные удобные методы
    @classmethod
    def create_demo_client(cls, messages_per_second: int = 5) -> 'AsyncClient':
        """Создает клиент для demo сервера."""
        return cls(EndPoints.PROTOBUF_DEMO_HOST, EndPoints.PROTOBUF_PORT, messages_per_second)

    @classmethod
    def create_live_client(cls, messages_per_second: int = 5) -> 'AsyncClient':
        """Создает клиент для live сервера."""
        return cls(EndPoints.PROTOBUF_LIVE_HOST, EndPoints.PROTOBUF_PORT, messages_per_second) 