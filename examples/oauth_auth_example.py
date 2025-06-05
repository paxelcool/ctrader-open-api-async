#!/usr/bin/env python3
"""Пример OAuth авторизации для cTrader Open API Async."""

import asyncio
import logging
import webbrowser
from http.server import HTTPServer, BaseHTTPRequestHandler
from threading import Thread
from urllib.parse import parse_qs, urlparse
from typing import Optional

from ctrader_open_api_async import AsyncClient, AsyncAuth, EndPoints
from ctrader_open_api_async.messages.OpenApiMessages_pb2 import *

# Настройка логирования
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class OAuthRedirectHandler(BaseHTTPRequestHandler):
    """Обработчик HTTP запросов для OAuth редиректа."""
    
    authorization_code: Optional[str] = None
    
    def do_GET(self):
        """Обработка GET запроса с кодом авторизации."""
        parsed_url = urlparse(self.path)
        query_params = parse_qs(parsed_url.query)
        
        if 'code' in query_params:
            OAuthRedirectHandler.authorization_code = query_params['code'][0]
            
            # Отправляем ответ пользователю
            self.send_response(200)
            self.send_header('Content-type', 'text/html; charset=utf-8')
            self.end_headers()
            
            html_response = """
            <!DOCTYPE html>
            <html>
            <head>
                <title>Авторизация завершена</title>
                <meta charset="utf-8">
            </head>
            <body>
                <h1>✅ Авторизация успешно завершена!</h1>
                <p>Вы можете закрыть это окно и вернуться к приложению.</p>
                <script>
                    setTimeout(() => window.close(), 3000);
                </script>
            </body>
            </html>
            """
            self.wfile.write(html_response.encode('utf-8'))
            logger.info(f"Получен код авторизации: {OAuthRedirectHandler.authorization_code}")
        else:
            # Обработка ошибки
            self.send_response(400)
            self.send_header('Content-type', 'text/html; charset=utf-8')
            self.end_headers()
            
            error = query_params.get('error', ['Неизвестная ошибка'])[0]
            error_description = query_params.get('error_description', [''])[0]
            
            html_response = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <title>Ошибка авторизации</title>
                <meta charset="utf-8">
            </head>
            <body>
                <h1>❌ Ошибка авторизации</h1>
                <p><strong>Ошибка:</strong> {error}</p>
                <p><strong>Описание:</strong> {error_description}</p>
            </body>
            </html>
            """
            self.wfile.write(html_response.encode('utf-8'))
            logger.error(f"Ошибка авторизации: {error} - {error_description}")
    
    def log_message(self, format, *args):
        """Отключаем логи HTTP сервера."""
        pass


class CTraderOAuthExample:
    """Пример полной OAuth авторизации для cTrader API."""
    
    def __init__(
        self,
        client_id: str,
        client_secret: str,
        redirect_uri: str = "http://localhost:8080/auth/callback",
        is_live: bool = False,
    ):
        """Инициализация примера OAuth авторизации.
        
        Args:
            client_id: ID приложения из cTrader
            client_secret: Секрет приложения из cTrader
            redirect_uri: URI для редиректа (должен быть зарегистрирован в приложении)
            is_live: Использовать live сервер (по умолчанию demo)
        """
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri
        self.is_live = is_live
        
        # Извлекаем порт из redirect_uri для локального сервера
        parsed_uri = urlparse(redirect_uri)
        self.server_port = parsed_uri.port or 8080
        
        self.access_token: Optional[str] = None
        self.refresh_token: Optional[str] = None
        self.account_id: Optional[int] = None
        
        # Выбор хоста для API
        host = EndPoints.PROTOBUF_LIVE_HOST if is_live else EndPoints.PROTOBUF_DEMO_HOST
        self.client = AsyncClient(host, EndPoints.PROTOBUF_PORT)
    
    def start_local_server(self) -> HTTPServer:
        """Запуск локального HTTP сервера для обработки OAuth редиректа."""
        server = HTTPServer(('localhost', self.server_port), OAuthRedirectHandler)
        server_thread = Thread(target=server.serve_forever)
        server_thread.daemon = True
        server_thread.start()
        logger.info(f"Локальный сервер запущен на порту {self.server_port}")
        return server
    
    async def perform_oauth_flow(self, scope: str = "trading") -> bool:
        """Выполнение полного OAuth потока авторизации.
        
        Args:
            scope: Область доступа ('accounts' для только чтения, 'trading' для торговли)
            
        Returns:
            True если авторизация успешна, False иначе
        """
        try:
            # 1. Запускаем локальный сервер для обработки редиректа
            server = self.start_local_server()
            
            # 2. Создаем объект для работы с OAuth
            async with AsyncAuth(self.client_id, self.client_secret, self.redirect_uri) as auth:
                
                # 3. Получаем URL для авторизации
                auth_url = auth.get_auth_uri(scope=scope)
                logger.info(f"URL для авторизации: {auth_url}")
                
                # 4. Открываем браузер для авторизации пользователя
                print(f"\n🌐 Открывается браузер для авторизации...")
                print(f"Если браузер не открылся, перейдите по ссылке: {auth_url}\n")
                webbrowser.open(auth_url)
                
                # 5. Ждем код авторизации
                logger.info("Ожидание кода авторизации...")
                timeout = 300  # 5 минут
                for _ in range(timeout):
                    if OAuthRedirectHandler.authorization_code:
                        break
                    await asyncio.sleep(1)
                else:
                    raise TimeoutError("Таймаут ожидания кода авторизации")
                
                # 6. Обмениваем код на токен доступа
                auth_code = OAuthRedirectHandler.authorization_code
                token_data = await auth.get_token(auth_code)
                
                self.access_token = token_data['access_token']
                self.refresh_token = token_data.get('refresh_token')
                
                logger.info("✅ OAuth авторизация успешно завершена!")
                logger.info(f"Access Token получен (длина: {len(self.access_token)})")
                
            # 7. Останавливаем локальный сервер
            server.shutdown()
            return True
            
        except Exception as e:
            logger.error(f"Ошибка OAuth авторизации: {e}")
            return False
    
    async def connect_and_authenticate(self) -> bool:
        """Подключение к API и аутентификация."""
        try:
            # Подключение к cTrader API
            await self.client.start_service()
            logger.info("Подключено к cTrader Open API")
            
            # Аутентификация приложения
            auth_response = await self.client.send_application_auth_req(
                self.client_id, self.client_secret
            )
            logger.info("Аутентификация приложения успешна")
            
            return True
            
        except Exception as e:
            logger.error(f"Ошибка подключения к API: {e}")
            return False
    
    async def get_accounts(self) -> list:
        """Получение списка аккаунтов по access token."""
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
    
    async def get_trader_info(self) -> Optional[dict]:
        """Получение информации о трейдере."""
        if not self.account_id:
            logger.error("Аккаунт не выбран")
            return None
        
        try:
            response = await self.client.send_trader_req(self.account_id)
            trader = response.trader
            
            info = {
                'balance': trader.balance,
                'total_margin_used': trader.totalMarginUsed,
                'total_unrealized_gross_pnl': trader.totalUnrealizedGrossPnL,
                'money_digits': trader.moneyDigits,
                'registration_timestamp': trader.registrationTimestamp,
            }
            
            logger.info(f"Информация о трейдере: {info}")
            return info
            
        except Exception as e:
            logger.error(f"Ошибка получения информации о трейдере: {e}")
            return None
    
    async def get_symbols(self, limit: int = 10) -> list:
        """Получение списка символов."""
        if not self.account_id:
            logger.error("Аккаунт не выбран")
            return []
        
        try:
            response = await self.client.send_symbols_list_req(self.account_id)
            symbols = list(response.symbol)
            
            logger.info(f"Найдено символов: {len(symbols)}")
            
            # Показываем первые символы
            for i, symbol in enumerate(symbols[:limit]):
                logger.info(f"Символ {i+1}: {symbol.symbolName} (ID: {symbol.symbolId})")
            
            return symbols
            
        except Exception as e:
            logger.error(f"Ошибка получения символов: {e}")
            return []
    
    async def cleanup(self):
        """Очистка ресурсов."""
        try:
            if self.account_id:
                await self.client.send_account_logout_req(self.account_id)
                logger.info("Выход из торгового аккаунта")
            
            await self.client.stop_service()
            logger.info("Отключено от cTrader Open API")
            
        except Exception as e:
            logger.error(f"Ошибка при очистке ресурсов: {e}")


async def main():
    """Основная функция примера OAuth авторизации."""
    
    # ВАЖНО: Замените эти значения на ваши реальные данные из cTrader
    CLIENT_ID = "your_client_id"
    CLIENT_SECRET = "your_client_secret"
    REDIRECT_URI = "http://localhost:8080/auth/callback"  # Должен быть зарегистрирован в приложении
    IS_LIVE = False  # True для live сервера, False для demo
    
    if CLIENT_ID == "your_client_id":
        print("❌ ОШИБКА: Укажите ваши реальные CLIENT_ID и CLIENT_SECRET")
        print("\n📋 Для получения учетных данных:")
        print("1. Зайдите в cTrader ID Portal: https://id.ctrader.com/")
        print("2. Создайте новое приложение в разделе 'Applications'")
        print("3. Добавьте redirect URI: http://localhost:8080/auth/callback")
        print("4. Скопируйте Client ID и Client Secret в этот код")
        return
    
    example = CTraderOAuthExample(
        CLIENT_ID, 
        CLIENT_SECRET, 
        REDIRECT_URI, 
        IS_LIVE
    )
    
    try:
        print("🚀 Начинаем процесс OAuth авторизации для cTrader Open API")
        print("=" * 60)
        
        # 1. Выполняем OAuth авторизацию
        print("\n1️⃣ Выполнение OAuth авторизации...")
        if not await example.perform_oauth_flow(scope="trading"):
            print("❌ Не удалось выполнить OAuth авторизацию")
            return
        
        # 2. Подключаемся к API
        print("\n2️⃣ Подключение к cTrader API...")
        if not await example.connect_and_authenticate():
            print("❌ Не удалось подключиться к API")
            return
        
        # 3. Получаем аккаунты
        print("\n3️⃣ Получение списка аккаунтов...")
        accounts = await example.get_accounts()
        if not accounts:
            print("❌ Не найдено доступных аккаунтов")
            return
        
        # 4. Получаем информацию о трейдере
        print("\n4️⃣ Получение информации о трейдере...")
        trader_info = await example.get_trader_info()
        
        # 5. Получаем символы
        print("\n5️⃣ Получение списка торговых символов...")
        symbols = await example.get_symbols(limit=5)
        
        print("\n✅ Все операции выполнены успешно!")
        print("🎉 Теперь вы можете использовать API для торговых операций")
        
    except KeyboardInterrupt:
        print("\n⚠️ Прервано пользователем")
    except Exception as e:
        logger.error(f"Неожиданная ошибка: {e}")
        print(f"\n❌ Произошла ошибка: {e}")
    finally:
        print("\n🧹 Очистка ресурсов...")
        await example.cleanup()


if __name__ == "__main__":
    print("cTrader Open API - Пример OAuth авторизации")
    print("=" * 50)
    asyncio.run(main()) 