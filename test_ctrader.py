import json
import logging
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Optional
from urllib.parse import parse_qs, urlparse

from ctrader_open_api import Protobuf
from ctrader_open_api.messages.OpenApiModelMessages_pb2 import (
    ProtoOAOrderType,
    ProtoOATradeSide,
)
from google.protobuf.json_format import MessageToJson
from twisted.internet import reactor
from twisted.internet.defer import Deferred, inlineCallbacks

from ctrader_connector import CTraderConnector

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class RedirectHandler(BaseHTTPRequestHandler):
    """Обработчик HTTP-запросов для редиректа авторизации."""

    def __init__(self, auth_callback: callable, *args, **kwargs):
        self.auth_callback = auth_callback
        super().__init__(*args, **kwargs)

    def do_GET(self):
        """Обработка GET-запроса с кодом авторизации."""
        parsed_path = urlparse(self.path)
        query_params = parse_qs(parsed_path.query)
        auth_code = query_params.get('code', [None])[0]
        if auth_code:
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(b"Authorization successful, you can close this page.")
            self.auth_callback(auth_code)
        else:
            self.send_response(400)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(b"Error: Invalid or empty authorization code.")

class TestCTrader:
    """Тестовый класс для проверки функциональности CTraderConnector."""

    def __init__(self, credentials_path: str):
        self.connector = CTraderConnector(credentials_path)
        self.account_id: Optional[int] = None
        self.symbol_id: Optional[int] = None
        self.position_id: Optional[int] = None
        self.volume = 100  # Начальный объем, будет изменен в зависимости от символа
        self.symbol_name: Optional[str] = None
        self.auth_code: Optional[str] = None
        self.server: Optional[HTTPServer] = None

    @inlineCallbacks
    def run(self):
        """Запуск тестового сценария."""
        try:
            # Авторизация
            yield self.authorize()
            # Ожидание авторизации приложения
            yield self.wait_for_app_auth()
            # Получение списка аккаунтов
            yield self.get_account_list()
            # Установка аккаунта
            yield self.set_account()
            # Получение списка символов
            yield self.get_symbols()
            # Открытие сделки
            yield self.open_trade()
            # Ожидание 30 секунд
            logger.info("Ожидание 30 секунд перед закрытием сделки")
            yield self.sleep(30)
            # Закрытие сделки
            yield self.close_trade()
        except Exception as e:
            logger.error(f"Ошибка выполнения теста: {e}")
        finally:
            if self.server:
                self.server.server_close()
            # Остановка реактора только если он запущен
            if reactor.running:
                reactor.stop()

    def start_redirect_server(self):
        """Запуск временного HTTP-сервера для редиректа."""
        def auth_callback(auth_code: str):
            self.auth_code = auth_code

        server_address = ('localhost', 8080)
        self.server = HTTPServer(server_address, lambda *args, **kwargs: RedirectHandler(auth_callback, *args, **kwargs))
        server_thread = threading.Thread(target=self.server.serve_forever)
        server_thread.daemon = True
        server_thread.start()
        logger.info("HTTP-сервер запущен на http://localhost:8080")

    @inlineCallbacks
    def authorize(self):
        """Авторизация с использованием токена или редиректа."""
        if self.connector.token:
            try:
                yield self.connector.ensure_token_valid()
                logger.info("Токен действителен")
                return
            except Exception as e:
                logger.error(f"Ошибка проверки токена: {e}")

        # Если токена нет или он недействителен, выполняем авторизацию
        auth_uri = self.connector.get_auth_uri()
        logger.info(f"Откройте браузер по адресу: {auth_uri}")
        self.start_redirect_server()
        webbrowser.open(auth_uri)
        # Ожидание получения кода авторизации
        yield self.wait_for_auth()
        yield self.connector.get_token(self.auth_code)
        if self.server:
            self.server.server_close()
            self.server = None

    def wait_for_auth(self) -> Deferred:
        """Ожидание получения кода авторизации."""
        d = Deferred()
        def check_auth():
            if self.auth_code:
                d.callback(None)
            else:
                reactor.callLater(1, check_auth)
        check_auth()
        return d

    def wait_for_app_auth(self) -> Deferred:
        """Ожидание авторизации приложения."""
        d = Deferred()

        def check_auth():
            # Проверяем, что клиент подключен и приложение авторизовано
            if self.connector.client and self.connector.client.isConnected:
                # Даем время на обработку сообщения авторизации
                reactor.callLater(2, d.callback, None)
            else:
                reactor.callLater(1, check_auth)

        check_auth()
        return d

    @inlineCallbacks
    def get_account_list(self):
        """Получение списка доступных аккаунтов."""
        response = yield self.connector.send_get_account_list_by_access_token_req()
        response_data = json.loads(MessageToJson(Protobuf.extract(response)))
        logger.info(f"Ответ от сервера: {response_data}")

        if "ctidTraderAccount" not in response_data:
            raise ValueError(f"Отсутствует поле ctidTraderAccount в ответе: {response_data}")

        accounts = response_data["ctidTraderAccount"]
        if accounts:
            self.account_id = int(accounts[0]["ctidTraderAccountId"])
            logger.info(f"Выбран аккаунт: {self.account_id}")
        else:
            raise ValueError("Аккаунты не найдены")

    @inlineCallbacks
    def set_account(self):
        """Установка текущего аккаунта."""
        yield self.connector.set_account(self.account_id)
        logger.info(f"Аккаунт {self.account_id} установлен")

    @inlineCallbacks
    def get_symbols(self):
        """Получение списка символов и поиск BTCUSD для торговли."""
        response = yield self.connector.send_symbols_list_req()
        symbols = json.loads(MessageToJson(Protobuf.extract(response)))["symbol"]

        logger.info(f"Получено {len(symbols)} символов")

        # Ищем BTCUSD
        btcusd_found = False
        for symbol in symbols:
            symbol_name = symbol["symbolName"]
            symbol_id = int(symbol["symbolId"])

            # Ищем точное совпадение с BTCUSD
            if symbol_name == "BTCUSD":
                self.symbol_id = symbol_id
                self.symbol_name = symbol_name
                self.volume = 1  # 0.01 в центах = 1
                logger.info(f"Найден целевой символ BTCUSD, ID: {self.symbol_id}, объем: 0.01 (в центах: {self.volume})")
                btcusd_found = True
                return

        if not btcusd_found:
            # Если BTCUSD не найден, ищем любой символ с BTC
            for symbol in symbols:
                symbol_name = symbol["symbolName"]
                if "BTC" in symbol_name and "USD" in symbol_name:
                    self.symbol_id = int(symbol["symbolId"])
                    self.symbol_name = symbol_name
                    self.volume = 1  # 0.01 в центах = 1
                    logger.info(f"BTCUSD не найден, используем альтернативный BTC символ: {symbol_name}, ID: {self.symbol_id}, объем: 0.01 (в центах: {self.volume})")
                    return

            # Если и BTC символов нет, берем первый доступный
            if symbols:
                first_symbol = symbols[0]
                self.symbol_id = int(first_symbol["symbolId"])
                self.symbol_name = first_symbol["symbolName"]
                # Для обычных валютных пар используем стандартный объем
                self.volume = 1000 if "BTC" not in self.symbol_name else 1
                logger.info(f"BTC символы не найдены, выбран первый доступный символ: {self.symbol_name}, ID: {self.symbol_id}, объем: {self.volume/100}")
            else:
                raise ValueError("Символы не найдены")

    @inlineCallbacks
    def open_trade(self):
        """Открытие тестовой сделки."""
        try:
            volume_display = self.volume / 100  # Показываем реальный объем
            logger.info(f"Открываем сделку на символе {self.symbol_name} (ID: {self.symbol_id}) с объемом {volume_display}")
            response = yield self.connector.send_new_order_req(
                symbol_id=self.symbol_id,
                order_type=ProtoOAOrderType.MARKET,
                trade_side=ProtoOATradeSide.BUY,
                volume=self.volume
            )
            response_data = json.loads(MessageToJson(Protobuf.extract(response)))
            logger.info(f"Ответ на открытие сделки: {response_data}")

            if "position" in response_data and "positionId" in response_data["position"]:
                self.position_id = int(response_data["position"]["positionId"])
                logger.info(f"Позиция создана, ID: {self.position_id}")
            elif "deal" in response_data:
                self.deal_id = response_data["deal"]["dealId"]
                if "positionId" in response_data["deal"]:
                    self.position_id = int(response_data["deal"]["positionId"])
                    logger.info(f"Сделка исполнена, позиция ID: {self.position_id}")
                else:
                    logger.info(f"Сделка открыта, ID: {self.deal_id}")
            else:
                logger.warning("Сделка не была открыта, возможно рынок закрыт")

        except Exception as e:
            logger.error(f"Ошибка открытия сделки: {e}")
            # Если рынок закрыт, это не критическая ошибка
            if "MARKET_CLOSED" in str(e):
                logger.info("Рынок закрыт, торговля недоступна")
            else:
                raise

    @inlineCallbacks
    def close_trade(self):
        """Закрытие сделки."""
        if not hasattr(self, 'position_id') or not self.position_id:
            logger.info("Нет открытых позиций для закрытия")
            return

        try:
            volume_display = self.volume / 100
            logger.info(f"Закрываем позицию {self.position_id} с объемом {volume_display}")
            response = yield self.connector.send_close_position_req(
                position_id=self.position_id,
                volume=self.volume
            )
            response_data = json.loads(MessageToJson(Protobuf.extract(response)))
            logger.info(f"Ответ на закрытие позиции: {response_data}")

            # Ждем дополнительно 10 секунд для получения сообщения о полном закрытии
            logger.info("Ожидание подтверждения закрытия позиции...")
            yield self.sleep(10)
            logger.info("Процесс закрытия позиции завершен")
        except Exception as e:
            logger.error(f"Ошибка закрытия позиции: {e}")

    def sleep(self, seconds: int) -> Deferred:
        """Асинхронное ожидание."""
        d = Deferred()
        reactor.callLater(seconds, d.callback, None)
        return d

if __name__ == "__main__":
    test = TestCTrader("credentials.json")
    test.run()
    reactor.run()
