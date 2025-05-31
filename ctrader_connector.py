import json
import logging
import os
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from urllib.parse import urlencode

from ctrader_open_api import Client, EndPoints, Protobuf, TcpProtocol
from ctrader_open_api.messages.OpenApiCommonMessages_pb2 import *
from ctrader_open_api.messages.OpenApiMessages_pb2 import *
from ctrader_open_api.messages.OpenApiModelMessages_pb2 import *
from google.protobuf.json_format import MessageToJson
from twisted.internet import reactor
from twisted.internet.defer import Deferred
from twisted.web.client import Agent
from twisted.web.http_headers import Headers
from twisted.web.iweb import IBodyProducer
from zope.interface import implementer

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@implementer(IBodyProducer)
class StringProducer:
    """Продюсер для передачи строковых данных в HTTP-запросах Twisted."""
    def __init__(self, body):
        self.body = body
        self.length = len(body)

    def startProducing(self, consumer):
        consumer.write(self.body)
        from twisted.internet.defer import succeed
        return succeed(None)

    def pauseProducing(self):
        pass

    def stopProducing(self):
        pass

class CTraderConnector:
    """Класс-обертка для взаимодействия с cTrader Open API."""

    def __init__(self, credentials_path: str, tokens_path: str = "tokens.json"):
        """Инициализация коннектора.

        Args:
            credentials_path: Путь к файлу с учетными данными (clientId, clientSecret, host).
            tokens_path: Путь к файлу для хранения токенов.
        """
        self.credentials_path = credentials_path
        self.tokens_path = tokens_path
        self.client_id: Optional[str] = None
        self.client_secret: Optional[str] = None
        self.host_type: Optional[str] = None
        self.current_account_id: Optional[int] = None
        self.token: Optional[Dict[str, Any]] = None
        self.client: Optional[Client] = None
        self.load_credentials()
        self.load_tokens()
        self.setup_client()

    def load_credentials(self) -> None:
        """Загрузка учетных данных из файла."""
        try:
            with open(self.credentials_path) as f:
                creds = json.load(f)
                self.client_id = creds["clientId"]
                self.client_secret = creds["Secret"]
                self.host_type = creds["Host"].lower()
        except Exception as e:
            logger.error(f"Ошибка загрузки учетных данных: {e}")
            raise

    def load_tokens(self) -> None:
        """Загрузка токенов из файла, если они существуют."""
        if os.path.exists(self.tokens_path):
            try:
                with open(self.tokens_path) as f:
                    self.token = json.load(f)
                    logger.info("Токены успешно загружены")
            except Exception as e:
                logger.error(f"Ошибка загрузки токенов: {e}")
                self.token = None

    def save_tokens(self, token_data: Dict[str, Any]) -> None:
        """Сохранение токенов в файл."""
        try:
            with open(self.tokens_path, 'w') as f:
                json.dump(token_data, f)
            logger.info("Токены сохранены")
        except Exception as e:
            logger.error(f"Ошибка сохранения токенов: {e}")

    def setup_client(self) -> None:
        """Настройка клиента cTrader."""
        host = EndPoints.PROTOBUF_LIVE_HOST if self.host_type == "live" else EndPoints.PROTOBUF_DEMO_HOST
        self.client = Client(host, EndPoints.PROTOBUF_PORT, TcpProtocol)
        self.client.setConnectedCallback(self.on_connected)
        self.client.setDisconnectedCallback(self.on_disconnected)
        self.client.setMessageReceivedCallback(self.on_message_received)
        self.client.startService()

    def on_connected(self, client: Client) -> None:
        """Обработчик подключения клиента."""
        logger.info("Клиент подключен")
        self.send_application_auth()

    def on_disconnected(self, client: Client, reason: str) -> None:
        """Обработчик отключения клиента."""
        logger.info(f"Клиент отключен, причина: {reason}")

    def on_message_received(self, client: Client, message: Any) -> None:
        """Обработчик входящих сообщений."""
        if message.payloadType == ProtoHeartbeatEvent().payloadType:
            return

        # Обработка ответа на авторизацию приложения
        if message.payloadType == ProtoOAApplicationAuthRes().payloadType:
            logger.info("Приложение авторизовано")
            return

        # Обработка ответа на авторизацию аккаунта
        if message.payloadType == ProtoOAAccountAuthRes().payloadType:
            response = Protobuf.extract(message)
            logger.info(f"Аккаунт {response.ctidTraderAccountId} авторизован")
            return

        # Преобразуем сообщение в JSON для человекочитаемого вывода
        try:
            extracted_message = Protobuf.extract(message)
            message_json = MessageToJson(extracted_message)
            message_data = json.loads(message_json)

            # Специальная обработка для торговых событий
            if message.payloadType == 2126:  # ProtoOAExecutionEvent
                execution_type = message_data.get("executionType", "")
                if execution_type == "ORDER_FILLED":
                    order_info = message_data.get("order", {})
                    is_closing = order_info.get("closingOrder", False)
                    if is_closing:
                        logger.info("🔴 ПОЗИЦИЯ ПОЛНОСТЬЮ ЗАКРЫТА!")
                    else:
                        logger.info("🟢 ПОЗИЦИЯ ОТКРЫТА!")
                elif execution_type == "ORDER_ACCEPTED":
                    order_info = message_data.get("order", {})
                    is_closing = order_info.get("closingOrder", False)
                    if is_closing:
                        logger.info("⏳ Закрывающий ордер принят, ожидание исполнения...")
                    else:
                        logger.info("⏳ Открывающий ордер принят, ожидание исполнения...")

            logger.info(f"Получено сообщение типа {message.payloadType}:")
            logger.info(f"Содержимое: {message_json}")
        except Exception as e:
            logger.warning(f"Не удалось преобразовать сообщение в JSON: {e}")
            logger.info(f"Получено сообщение типа {message.payloadType} (бинарные данные)")

    def send_application_auth(self) -> Deferred:
        """Отправка запроса на аутентификацию приложения."""
        request = ProtoOAApplicationAuthReq()
        request.clientId = self.client_id
        request.clientSecret = self.client_secret
        return self.client.send(request)

    def get_auth_uri(self) -> str:
        """Получение URL для авторизации."""
        params = {
            "client_id": self.client_id,
            "redirect_uri": "http://localhost:8080/redirect",
            "response_type": "code",
            "scope": "trading"
        }
        return f"https://openapi.ctrader.com/apps/auth?{urlencode(params)}"

    def get_token(self, auth_code: str) -> Deferred:
        """Получение токена по коду авторизации."""
        from twisted.web.client import readBody

        agent = Agent(reactor)
        url = b"https://openapi.ctrader.com/apps/token"
        headers = Headers({
            b"Content-Type": [b"application/x-www-form-urlencoded"],
            b"Accept": [b"application/json"]
        })
        request_body = urlencode({
            "grant_type": "authorization_code",
            "code": auth_code,
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "redirect_uri": "http://localhost:8080/redirect"
        }).encode("utf-8")

        body_producer = StringProducer(request_body)

        def handle_response(response):
            return readBody(response)

        def handle_body(body_bytes):
            return self._process_token_response(body_bytes)

        def handle_error(failure):
            logger.error(f"Ошибка при получении токена: {failure}")
            return failure

        d = agent.request(b"POST", url, headers, body_producer)
        d.addCallback(handle_response)
        d.addCallback(handle_body)
        d.addErrback(handle_error)
        return d

    def _process_token_response(self, body_bytes):
        """Обработка ответа с токеном."""
        try:
            token_data = json.loads(body_bytes.decode("utf-8"))
            logger.info(f"Получен ответ от сервера токенов: {token_data}")

            if "errorCode" in token_data and token_data["errorCode"] is not None:
                error_msg = token_data.get('description', f"Ошибка {token_data['errorCode']}")
                logger.error(f"Ошибка получения токена: {error_msg}")
                raise ValueError(error_msg)

            if "access_token" not in token_data:
                logger.error(f"Отсутствует access_token в ответе: {token_data}")
                raise ValueError("Отсутствует access_token в ответе сервера")

            self.token = token_data
            self.save_tokens(token_data)
            logger.info("Токен успешно получен и сохранен")
            return token_data
        except json.JSONDecodeError as e:
            logger.error(f"Ошибка декодирования JSON: {e}")
            logger.error(f"Тело ответа: {body_bytes}")
            raise ValueError(f"Некорректный JSON в ответе: {e}")
        except Exception as e:
            logger.error(f"Неожиданная ошибка при обработке токена: {e}")
            raise

    def refresh_token(self) -> Deferred:
        """Обновление токена."""
        if not self.token or "refresh_token" not in self.token:
            raise ValueError("Отсутствует токен обновления")

        from twisted.web.client import readBody

        agent = Agent(reactor)
        url = b"https://openapi.ctrader.com/apps/token"
        headers = Headers({
            b"Content-Type": [b"application/x-www-form-urlencoded"],
            b"Accept": [b"application/json"]
        })
        request_body = urlencode({
            "grant_type": "refresh_token",
            "refresh_token": self.token["refresh_token"],
            "client_id": self.client_id,
            "client_secret": self.client_secret
        }).encode("utf-8")

        body_producer = StringProducer(request_body)

        def handle_response(response):
            return readBody(response)

        def handle_body(body_bytes):
            return self._process_token_response(body_bytes)

        d = agent.request(b"POST", url, headers, body_producer)
        d.addCallback(handle_response)
        d.addCallback(handle_body)
        return d

    def ensure_token_valid(self) -> Deferred:
        """Проверка и обновление токена, если необходимо."""
        if not self.token:
            raise ValueError("Токен отсутствует, требуется авторизация")

        # Проверяем, есть ли поля expires_in и issued_at
        if "expires_in" not in self.token or "issued_at" not in self.token:
            # Если нет, считаем токен действительным
            d = Deferred()
            d.callback(None)
            return d

        expires_at = datetime.fromtimestamp(self.token["expires_in"] + self.token["issued_at"])
        if datetime.now() < expires_at - timedelta(minutes=5):
            d = Deferred()
            d.callback(None)
            return d
        return self.refresh_token()

    def set_account(self, account_id: int) -> Deferred:
        """Установка текущего аккаунта."""
        self.current_account_id = account_id
        request = ProtoOAAccountAuthReq()
        request.ctidTraderAccountId = account_id
        request.accessToken = self.token["access_token"]
        return self.client.send(request)

    # Реализация методов API согласно документации
    def send_version_req(self, client_msg_id: Optional[str] = None) -> Deferred:
        """Запрос версии API."""
        request = ProtoOAVersionReq()
        return self.client.send(request, clientMsgId=client_msg_id)

    def send_get_account_list_by_access_token_req(self, client_msg_id: Optional[str] = None) -> Deferred:
        """Запрос списка аккаунтов по токену."""
        request = ProtoOAGetAccountListByAccessTokenReq()
        request.accessToken = self.token["access_token"]
        return self.client.send(request, clientMsgId=client_msg_id)

    def send_account_logout_req(self, client_msg_id: Optional[str] = None) -> Deferred:
        """Запрос на выход из аккаунта."""
        request = ProtoOAAccountLogoutReq()
        request.ctidTraderAccountId = self.current_account_id
        return self.client.send(request, clientMsgId=client_msg_id)

    def send_asset_list_req(self, client_msg_id: Optional[str] = None) -> Deferred:
        """Запрос списка активов."""
        request = ProtoOAAssetListReq()
        request.ctidTraderAccountId = self.current_account_id
        return self.client.send(request, clientMsgId=client_msg_id)

    def send_asset_class_list_req(self, client_msg_id: Optional[str] = None) -> Deferred:
        """Запрос списка классов активов."""
        request = ProtoOAAssetClassListReq()
        request.ctidTraderAccountId = self.current_account_id
        return self.client.send(request, clientMsgId=client_msg_id)

    def send_symbol_category_list_req(self, client_msg_id: Optional[str] = None) -> Deferred:
        """Запрос списка категорий символов."""
        request = ProtoOASymbolCategoryListReq()
        request.ctidTraderAccountId = self.current_account_id
        return self.client.send(request, clientMsgId=client_msg_id)

    def send_symbols_list_req(self, include_archived: bool = False, client_msg_id: Optional[str] = None) -> Deferred:
        """Запрос списка символов."""
        request = ProtoOASymbolsListReq()
        request.ctidTraderAccountId = self.current_account_id
        request.includeArchivedSymbols = include_archived
        return self.client.send(request, clientMsgId=client_msg_id)

    def send_trader_req(self, client_msg_id: Optional[str] = None) -> Deferred:
        """Запрос информации о трейдере."""
        request = ProtoOATraderReq()
        request.ctidTraderAccountId = self.current_account_id
        return self.client.send(request, clientMsgId=client_msg_id)

    def send_subscribe_spots_req(self, symbol_ids: List[int], client_msg_id: Optional[str] = None) -> Deferred:
        """Подписка на спотовые котировки."""
        request = ProtoOASubscribeSpotsReq()
        request.ctidTraderAccountId = self.current_account_id
        request.symbolId.extend(symbol_ids)
        return self.client.send(request, clientMsgId=client_msg_id)

    def send_unsubscribe_spots_req(self, symbol_id: int, client_msg_id: Optional[str] = None) -> Deferred:
        """Отписка от спотовых котировок."""
        request = ProtoOAUnsubscribeSpotsReq()
        request.ctidTraderAccountId = self.current_account_id
        request.symbolId.append(symbol_id)
        return self.client.send(request, clientMsgId=client_msg_id)

    def send_reconcile_req(self, client_msg_id: Optional[str] = None) -> Deferred:
        """Запрос сверки позиций."""
        request = ProtoOAReconcileReq()
        request.ctidTraderAccountId = self.current_account_id
        return self.client.send(request, clientMsgId=client_msg_id)

    def send_get_trendbars_req(self, weeks: int, period: str, symbol_id: int, client_msg_id: Optional[str] = None) -> Deferred:
        """Запрос трендовых баров."""
        request = ProtoOAGetTrendbarsReq()
        request.ctidTraderAccountId = self.current_account_id
        request.period = ProtoOATrendbarPeriod.Value(period)
        request.fromTimestamp = int((datetime.utcnow() - timedelta(weeks=weeks)).timestamp() * 1000)
        request.toTimestamp = int(datetime.utcnow().timestamp() * 1000)
        request.symbolId = symbol_id
        return self.client.send(request, clientMsgId=client_msg_id)

    def send_get_tick_data_req(self, days: int, quote_type: str, symbol_id: int, client_msg_id: Optional[str] = None) -> Deferred:
        """Запрос тиковых данных."""
        request = ProtoOAGetTickDataReq()
        request.ctidTraderAccountId = self.current_account_id
        request.type = ProtoOAQuoteType.Value(quote_type.upper())
        request.fromTimestamp = int((datetime.utcnow() - timedelta(days=days)).timestamp() * 1000)
        request.toTimestamp = int(datetime.utcnow().timestamp() * 1000)
        request.symbolId = symbol_id
        return self.client.send(request, clientMsgId=client_msg_id)

    def send_new_order_req(self, symbol_id: int, order_type: int, trade_side: int, volume: int, price: Optional[float] = None, client_msg_id: Optional[str] = None) -> Deferred:
        """Создание нового ордера."""
        request = ProtoOANewOrderReq()
        request.ctidTraderAccountId = self.current_account_id
        request.symbolId = symbol_id
        request.orderType = order_type
        request.tradeSide = trade_side
        request.volume = volume  # Объем уже в центах
        if order_type == 2:  # LIMIT
            request.limitPrice = price
        elif order_type == 3:  # STOP
            request.stopPrice = price
        return self.client.send(request, clientMsgId=client_msg_id)

    def send_close_position_req(self, position_id: int, volume: int, client_msg_id: Optional[str] = None) -> Deferred:
        """Закрытие позиции."""
        request = ProtoOAClosePositionReq()
        request.ctidTraderAccountId = self.current_account_id
        request.positionId = position_id
        request.volume = volume  # Объем уже в центах
        return self.client.send(request, clientMsgId=client_msg_id)

    def send_cancel_order_req(self, order_id: int, client_msg_id: Optional[str] = None) -> Deferred:
        """Отмена ордера."""
        request = ProtoOACancelOrderReq()
        request.ctidTraderAccountId = self.current_account_id
        request.orderId = order_id
        return self.client.send(request, clientMsgId=client_msg_id)

    def send_deal_offset_list_req(self, deal_id: int, client_msg_id: Optional[str] = None) -> Deferred:
        """Запрос списка смещений сделки."""
        request = ProtoOADealOffsetListReq()
        request.ctidTraderAccountId = self.current_account_id
        request.dealId = deal_id
        return self.client.send(request, clientMsgId=client_msg_id)

    def send_get_position_unrealized_pnl_req(self, client_msg_id: Optional[str] = None) -> Deferred:
        """Запрос нереализованной прибыли/убытка."""
        request = ProtoOAGetPositionUnrealizedPnLReq()
        request.ctidTraderAccountId = self.current_account_id
        return self.client.send(request, clientMsgId=client_msg_id)

    def send_order_details_req(self, order_id: int, client_msg_id: Optional[str] = None) -> Deferred:
        """Запрос деталей ордера."""
        request = ProtoOAOrderDetailsReq()
        request.ctidTraderAccountId = self.current_account_id
        request.orderId = order_id
        return self.client.send(request, clientMsgId=client_msg_id)

    def send_order_list_by_position_id_req(self, position_id: int, from_timestamp: Optional[int] = None, to_timestamp: Optional[int] = None, client_msg_id: Optional[str] = None) -> Deferred:
        """Запрос списка ордеров по ID позиции."""
        request = ProtoOAOrderListByPositionIdReq()
        request.ctidTraderAccountId = self.current_account_id
        request.positionId = position_id
        return self.client.send(request, fromTimestamp=from_timestamp, toTimestamp=to_timestamp, clientMsgId=client_msg_id)
