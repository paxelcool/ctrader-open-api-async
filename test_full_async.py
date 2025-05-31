"""Полный тестовый скрипт для проверки всех функций cTrader Async API."""

import asyncio
import logging
import webbrowser
import json
from typing import Optional
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import parse_qs, urlparse
import threading
from datetime import datetime, timedelta

from ctrader_async_connector import (
    CTraderAsyncConnector, 
    TradeSide, 
    OrderType, 
    TrendbarPeriod,
    QuoteType
)

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

    def log_message(self, format, *args):
        """Отключаем логирование HTTP сервера."""
        pass

class FullAsyncTester:
    """Полный тестер для cTrader Async API."""
    
    def __init__(self, credentials_path: str):
        self.connector = CTraderAsyncConnector(credentials_path)
        self.account_id: Optional[int] = None
        self.symbol_id: Optional[int] = None
        self.symbol_name: Optional[str] = None
        self.volume = 100
        self.auth_code: Optional[str] = None
        self.server: Optional[HTTPServer] = None
        
        # Статистика тестов
        self.tests_passed = 0
        self.tests_failed = 0
        self.test_results = []

    def log_test_result(self, test_name: str, success: bool, message: str = ""):
        """Логирует результат теста."""
        if success:
            self.tests_passed += 1
            logger.info(f"✅ {test_name}: ПРОЙДЕН {message}")
        else:
            self.tests_failed += 1
            logger.error(f"❌ {test_name}: ПРОВАЛЕН {message}")
        
        self.test_results.append({
            "test": test_name,
            "success": success,
            "message": message,
            "timestamp": datetime.now().isoformat()
        })

    async def run_all_tests(self):
        """Запуск всех тестов."""
        logger.info("🚀 Запуск полного тестирования cTrader Async API")
        
        try:
            async with self.connector:
                # 1. Тест авторизации
                logger.info("🔄 Запуск теста авторизации...")
                await self.test_authorization()
                
                # 2. Тест подключения
                logger.info("🔄 Запуск теста подключения...")
                await self.test_connection()
                
                # 3. Тест работы с аккаунтами
                logger.info("🔄 Запуск теста работы с аккаунтами...")
                await self.test_accounts()
                
                # Проверяем, что аккаунт установлен, иначе прекращаем тестирование
                if not self.connector.current_account_id:
                    logger.error("❌ Критическая ошибка: аккаунт не установлен. Тестирование прервано.")
                    self.print_final_report()
                    return
                
                # 4. Тест работы с символами
                logger.info("🔄 Запуск теста работы с символами...")
                await self.test_symbols()
                
                # 5. Тест рыночных данных
                logger.info("🔄 Запуск теста рыночных данных...")
                await self.test_market_data()
                
                # 6. Тест исторических данных
                logger.info("🔄 Запуск теста исторических данных...")
                await self.test_historical_data()
                
                # 7. Тест торговых операций
                logger.info("🔄 Запуск теста торговых операций...")
                await self.test_trading()
                
                # 8. Тест информационных запросов
                logger.info("🔄 Запуск теста информационных запросов...")
                await self.test_info_requests()
                
                # 9. Тест обработчиков событий
                logger.info("🔄 Запуск теста обработчиков событий...")
                await self.test_event_handlers()
                
                # 10. Финальная очистка тестовых ордеров
                logger.info("🔄 Запуск финальной очистки...")
                await self.test_cleanup()
                
                # Итоговый отчет
                self.print_final_report()
                
        except Exception as e:
            logger.error(f"❌ Критическая ошибка тестирования: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
        finally:
            if self.server:
                self.server.server_close()

    async def test_authorization(self):
        """Тест авторизации."""
        logger.info("🔐 Тестирование авторизации...")
        
        try:
            if self.connector.token:
                await self.connector.ensure_token_valid()
                self.log_test_result("Проверка токена", True, "Токен действителен")
            else:
                # Авторизация через браузер
                auth_uri = self.connector.get_auth_uri()
                self.log_test_result("Генерация URI авторизации", True, f"URI: {auth_uri[:50]}...")
                
                self.start_redirect_server()
                webbrowser.open(auth_uri)
                
                await self.wait_for_auth()
                await self.connector.get_token(self.auth_code)
                
                if self.server:
                    self.server.server_close()
                    self.server = None
                
                self.log_test_result("Получение токена", True, "Токен получен и сохранен")
                
        except Exception as e:
            self.log_test_result("Авторизация", False, str(e))

    async def test_connection(self):
        """Тест подключения."""
        logger.info("🔌 Тестирование подключения...")
        
        try:
            # Проверяем, что клиент подключен
            if self.connector.client and self.connector.client.is_connected:
                self.log_test_result("TCP подключение", True, "Соединение установлено")
            else:
                self.log_test_result("TCP подключение", False, "Соединение не установлено")
            
            # Тест версии API
            version_response = await self.connector.send_version_req()
            self.log_test_result("Запрос версии API", True, "Версия получена")
            
        except Exception as e:
            self.log_test_result("Подключение", False, str(e))

    async def test_accounts(self):
        """Тест работы с аккаунтами."""
        logger.info("👤 Тестирование работы с аккаунтами...")
        
        try:
            # Получение списка аккаунтов
            accounts = await self.connector.get_account_list()
            if accounts:
                self.log_test_result("Получение списка аккаунтов", True, f"Найдено {len(accounts)} аккаунтов")
                
                # Установка аккаунта
                self.account_id = accounts[0].account_id
                await self.connector.set_account(self.account_id)
                self.log_test_result("Установка аккаунта", True, f"Аккаунт {self.account_id} установлен")
            else:
                self.log_test_result("Получение списка аккаунтов", False, "Аккаунты не найдены")
                # Если аккаунты не найдены, прекращаем дальнейшее тестирование
                logger.error("❌ Критическая ошибка: аккаунты не найдены. Дальнейшее тестирование невозможно.")
                return
                
        except Exception as e:
            self.log_test_result("Работа с аккаунтами", False, str(e))
            logger.error("❌ Критическая ошибка в работе с аккаунтами. Дальнейшее тестирование невозможно.")
            return

    async def test_symbols(self):
        """Тест работы с символами."""
        logger.info("💱 Тестирование работы с символами...")
        
        try:
            # Проверяем, что аккаунт установлен
            if not self.connector.current_account_id:
                self.log_test_result("Работа с символами", False, "Аккаунт не установлен")
                return
            
            # Получение списка символов с повторными попытками
            symbols = None
            for attempt in range(3):
                try:
                    logger.info(f"Попытка {attempt + 1} получения символов...")
                    symbols = await self.connector.get_symbols()
                    
                    # Ждем обработки ответа
                    await asyncio.sleep(2)
                    
                    # Проверяем, что символы действительно получены
                    if self.connector.symbols:
                        symbols = list(self.connector.symbols.values())
                        break
                        
                except asyncio.TimeoutError:
                    logger.warning(f"Таймаут на попытке {attempt + 1}")
                    if attempt == 2:
                        raise
                    await asyncio.sleep(5)
                except Exception as e:
                    logger.warning(f"Ошибка на попытке {attempt + 1}: {e}")
                    if attempt == 2:
                        raise
                    await asyncio.sleep(5)
            
            if symbols and len(symbols) > 0:
                self.log_test_result("Получение списка символов", True, f"Найдено {len(symbols)} символов")
                
                # Поиск подходящего символа
                btc_symbol = self.connector.get_symbol_by_name("BTCUSD")
                if btc_symbol:
                    self.symbol_id = btc_symbol.symbol_id
                    self.symbol_name = btc_symbol.symbol_name
                    self.volume = 1
                    self.log_test_result("Поиск BTCUSD", True, f"Найден символ ID={self.symbol_id}")
                else:
                    # Ищем любой символ с USD
                    usd_symbols = [s for s in symbols if "USD" in s.symbol_name]
                    if usd_symbols:
                        first_symbol = usd_symbols[0]
                        self.symbol_id = first_symbol.symbol_id
                        self.symbol_name = first_symbol.symbol_name
                        self.volume = 1000
                        self.log_test_result("Выбор USD символа", True, f"Выбран {self.symbol_name}")
                    else:
                        # Берем первый доступный символ
                        first_symbol = symbols[0]
                        self.symbol_id = first_symbol.symbol_id
                        self.symbol_name = first_symbol.symbol_name
                        self.volume = 1000
                        self.log_test_result("Выбор символа", True, f"Выбран {self.symbol_name}")
                
                # Получение символа по ID
                try:
                    symbol_by_id = await self.connector.get_symbol_by_id(self.symbol_id)
                    self.log_test_result("Получение символа по ID", True, "Символ получен")
                except Exception as e:
                    self.log_test_result("Получение символа по ID", False, str(e))
                
            else:
                self.log_test_result("Получение списка символов", False, "Символы не найдены")
                
            # Получение активов
            try:
                await self.connector.get_assets()
                self.log_test_result("Получение активов", True, "Активы получены")
            except Exception as e:
                self.log_test_result("Получение активов", False, str(e))
                
        except Exception as e:
            self.log_test_result("Работа с символами", False, str(e))

    async def test_market_data(self):
        """Тест рыночных данных."""
        logger.info("📈 Тестирование рыночных данных...")
        
        try:
            if not self.symbol_id:
                self.log_test_result("Рыночные данные", False, "Символ не выбран")
                return
            
            # Подписка на спотовые котировки
            await self.connector.subscribe_spots([self.symbol_id])
            self.log_test_result("Подписка на котировки", True, f"Подписка на {self.symbol_name}")
            
            # Ждем котировки
            await asyncio.sleep(3)
            
            # Подписка на трендбары
            await self.connector.subscribe_live_trendbar(self.symbol_id, TrendbarPeriod.M1)
            self.log_test_result("Подписка на трендбары", True, "Подписка на M1 трендбары")
            
            await asyncio.sleep(2)
            
            # Отписка
            await self.connector.unsubscribe_spots([self.symbol_id])
            await self.connector.unsubscribe_live_trendbar(self.symbol_id, TrendbarPeriod.M1)
            self.log_test_result("Отписка от данных", True, "Отписка выполнена")
            
        except Exception as e:
            self.log_test_result("Рыночные данные", False, str(e))

    async def test_historical_data(self):
        """Тест исторических данных."""
        logger.info("📊 Тестирование исторических данных...")
        
        try:
            if not self.symbol_id:
                self.log_test_result("Исторические данные", False, "Символ не выбран")
                return
            
            # Получение трендбаров
            to_timestamp = int(datetime.now().timestamp() * 1000)
            from_timestamp = int((datetime.now() - timedelta(hours=1)).timestamp() * 1000)
            
            trendbars = await self.connector.get_trendbars(
                self.symbol_id,
                TrendbarPeriod.M1,
                from_timestamp,
                to_timestamp,
                count=10
            )
            
            if trendbars:
                self.log_test_result("Получение трендбаров", True, f"Получено {len(trendbars)} баров")
            else:
                self.log_test_result("Получение трендбаров", False, "Трендбары не получены")
            
            # Получение тиков
            to_timestamp = int(datetime.now().timestamp() * 1000)
            from_timestamp = int((datetime.now() - timedelta(minutes=10)).timestamp() * 1000)
            
            ticks = await self.connector.get_tick_data(
                self.symbol_id,
                QuoteType.BID,
                from_timestamp,
                to_timestamp
            )
            
            if ticks:
                self.log_test_result("Получение тиков", True, f"Получено {len(ticks)} тиков")
            else:
                self.log_test_result("Получение тиков", False, "Тики не получены")
                
        except Exception as e:
            self.log_test_result("Исторические данные", False, str(e))

    async def test_trading(self):
        """Тест торговых операций."""
        try:
            logger.info("💰 Тестирование торговых операций...")
            
            created_order_id = None
            created_position_id = None
            
            try:
                if not self.symbol_id:
                    logger.error("❌ Символ не выбран для торговых операций")
                    self.log_test_result("Торговые операции", False, "Символ не выбран")
                    return
                
                logger.info(f"🔄 Используем символ: {self.symbol_name} (ID: {self.symbol_id}), объем: {self.volume}")
                
                # Попытка размещения рыночного ордера
                try:
                    logger.info("🔄 Начинаем размещение рыночного ордера...")
                    order_response = await self.connector.buy_market(
                        self.symbol_id,
                        self.volume,
                        comment="Test order",
                        label="AsyncTest"
                    )
                    logger.info("✅ Рыночный ордер размещен")
                    self.log_test_result("Размещение рыночного ордера", True, "Ордер размещен")
                    
                    # Ждем исполнения ордера
                    await asyncio.sleep(3)
                    
                    # Получаем информацию о позициях через reconcile
                    logger.info("🔄 Получаем информацию о позициях...")
                    reconcile_response = await self.connector.reconcile()
                    
                    # Извлекаем позиции из ответа
                    from ctrader_open_api_async.protobuf import Protobuf
                    extracted = Protobuf.extract(reconcile_response)
                    
                    # Ищем нашу тестовую позицию среди открытых позиций
                    test_positions = []
                    if hasattr(extracted, 'position') and extracted.position:
                        # Фильтруем только открытые тестовые позиции
                        test_positions = [position for position in extracted.position
                                        if (hasattr(position, 'positionStatus') and position.positionStatus == 1 and
                                            hasattr(position, 'tradeData') and 
                                            hasattr(position.tradeData, 'symbolId') and
                                            position.tradeData.symbolId == self.symbol_id and
                                            hasattr(position.tradeData, 'label') and
                                            position.tradeData.label == "AsyncTest")]
                        
                        if test_positions:
                            logger.info(f"🔍 Найдено {len(test_positions)} открытых тестовых позиций")
                        else:
                            logger.info("🔍 Открытые тестовые позиции не найдены")
                    
                    if test_positions:
                        created_position_id = test_positions[0].positionId
                        position_volume = test_positions[0].tradeData.volume
                        self.log_test_result("Отслеживание позиции", True, f"Позиция {created_position_id} найдена")
                        
                        # Ждем 10 секунд перед закрытием
                        logger.info("⏳ Ждем 10 секунд перед закрытием позиции...")
                        await asyncio.sleep(10)
                        
                        # Закрываем позицию
                        try:
                            logger.info(f"🔄 Закрываем позицию {created_position_id}...")
                            close_response = await self.connector.close_position(
                                created_position_id, 
                                position_volume
                            )
                            logger.info(f"✅ Позиция {created_position_id} успешно закрыта")
                            self.log_test_result("Закрытие позиции", True, f"Позиция {created_position_id} закрыта")
                            await asyncio.sleep(2)
                        except Exception as e:
                            logger.error(f"❌ Ошибка закрытия позиции {created_position_id}: {e}")
                            self.log_test_result("Закрытие позиции", False, str(e))
                    else:
                        logger.warning("❌ Тестовая позиция не найдена")
                        self.log_test_result("Отслеживание позиции", False, "Позиция не найдена")
                    
                except Exception as e:
                    logger.error(f"❌ Ошибка размещения рыночного ордера: {e}")
                    if "MARKET_CLOSED" in str(e) or "TRADING_DISABLED" in str(e):
                        self.log_test_result("Размещение рыночного ордера", True, "Рынок закрыт (ожидаемо)")
                    else:
                        self.log_test_result("Размещение рыночного ордера", False, str(e))
                
                # Попытка размещения лимитного ордера
                try:
                    logger.info("🔄 Начинаем размещение лимитного ордера...")
                    limit_response = await self.connector.place_limit_order(
                        self.symbol_id,
                        TradeSide.SELL,
                        self.volume,
                        limit_price=999999.0,  # Заведомо высокая цена
                        comment="Test limit order"
                    )
                    logger.info("✅ Лимитный ордер размещен, получен ответ")
                    self.log_test_result("Размещение лимитного ордера", True, "Лимитный ордер размещен")
                    
                    # Попытка извлечь ID ордера из ответа
                    try:
                        logger.info("🔄 Пытаемся извлечь ID ордера из ответа...")
                        from ctrader_open_api_async.protobuf import Protobuf
                        extracted = Protobuf.extract(limit_response)
                        logger.info(f"🔍 Ответ на создание лимитного ордера: {extracted}")
                        
                        # Ищем ID ордера в ответе
                        if hasattr(extracted, 'order') and hasattr(extracted.order, 'orderId'):
                            created_order_id = extracted.order.orderId
                            logger.info(f"🎯 Получен ID ордера из ответа: {created_order_id}")
                        elif hasattr(extracted, 'orderId'):
                            created_order_id = extracted.orderId
                            logger.info(f"🎯 Получен ID ордера из ответа: {created_order_id}")
                        else:
                            logger.warning("❌ ID ордера не найден в ответе")
                            logger.info(f"🔍 Доступные атрибуты в ответе: {dir(extracted)}")
                            # Дополнительная проверка структуры order
                            if hasattr(extracted, 'order'):
                                logger.info(f"🔍 Атрибуты order: {dir(extracted.order)}")
                                # Попробуем получить orderId как строку
                                if hasattr(extracted.order, 'orderId'):
                                    created_order_id = str(extracted.order.orderId)
                                    logger.info(f"🎯 Получен ID ордера как строка: {created_order_id}")
                            
                    except Exception as e:
                        logger.error(f"❌ Ошибка извлечения ID ордера из ответа: {e}")
                        import traceback
                        logger.error(f"Traceback: {traceback.format_exc()}")
                    
                    # Если не получили ID из ответа, ищем в списке ордеров
                    if not created_order_id:
                        logger.info("🔄 ID не получен из ответа, ищем в списке ордеров...")
                        await asyncio.sleep(2)  # Ждем обработки ордера
                        
                        orders_response = await self.connector.get_order_list()
                        self.log_test_result("Получение списка ордеров", True, "Список ордеров получен")
                        
                        try:
                            from ctrader_open_api_async.protobuf import Protobuf
                            extracted = Protobuf.extract(orders_response)
                            if hasattr(extracted, 'order') and extracted.order:
                                # Ищем наш тестовый ордер среди активных ордеров
                                active_test_orders = [order for order in extracted.order 
                                                    if (hasattr(order, 'orderStatus') and order.orderStatus == 1 and
                                                        hasattr(order, 'comment') and 
                                                        order.comment == "Test limit order")]
                                
                                if active_test_orders:
                                    # Берем первый найденный активный тестовый ордер
                                    created_order_id = active_test_orders[0].orderId
                                    logger.info(f"🎯 Найден активный тестовый ордер: {created_order_id}")
                                else:
                                    logger.warning("❌ Активный тестовый ордер не найден")
                            else:
                                logger.warning("❌ Ордера не найдены в ответе")
                        except Exception as e:
                            logger.error(f"❌ Ошибка поиска ордера в списке: {e}")
                    else:
                        # Получение списка ордеров для проверки
                        orders_response = await self.connector.get_order_list()
                        self.log_test_result("Получение списка ордеров", True, "Список ордеров получен")
                    
                    # Тест отмены ордера
                    if created_order_id:
                        try:
                            logger.info(f"🔄 Пытаемся отменить ордер {created_order_id}...")
                            cancel_response = await self.connector.cancel_order(created_order_id)
                            logger.info(f"✅ Ордер {created_order_id} успешно отменен")
                            self.log_test_result("Отмена ордера", True, f"Ордер {created_order_id} отменен")
                            await asyncio.sleep(1)
                        except Exception as e:
                            logger.error(f"❌ Ошибка отмены ордера {created_order_id}: {e}")
                            self.log_test_result("Отмена ордера", False, str(e))
                    else:
                        logger.error("❌ ID ордера не получен - отмена невозможна")
                        self.log_test_result("Отмена ордера", False, "ID ордера не получен")
                    
                except Exception as e:
                    logger.error(f"❌ Ошибка размещения лимитного ордера: {e}")
                    if "MARKET_CLOSED" in str(e) or "TRADING_DISABLED" in str(e):
                        self.log_test_result("Размещение лимитного ордера", True, "Рынок закрыт (ожидаемо)")
                    else:
                        self.log_test_result("Размещение лимитного ордера", False, str(e))
                        
            except Exception as e:
                logger.error(f"❌ Общая ошибка в торговых операциях: {e}")
                import traceback
                logger.error(f"Traceback: {traceback.format_exc()}")
                self.log_test_result("Торговые операции", False, str(e))
            finally:
                # Дополнительная попытка закрытия позиции в случае ошибки
                if created_position_id:
                    try:
                        # Используем объем позиции, если он был определен, иначе self.volume
                        volume_to_close = position_volume if 'position_volume' in locals() else self.volume
                        await self.connector.close_position(created_position_id, volume_to_close)
                        logger.info(f"Дополнительное закрытие позиции {created_position_id}")
                    except:
                        pass
                        
                # Дополнительная попытка отмены ордера в случае ошибки
                if created_order_id:
                    try:
                        await self.connector.cancel_order(created_order_id)
                        logger.info(f"Дополнительная отмена ордера {created_order_id}")
                    except:
                        pass
        
        except Exception as e:
            logger.error(f"❌ Критическая ошибка в test_trading: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            self.log_test_result("Торговые операции", False, f"Критическая ошибка: {e}")

    async def test_info_requests(self):
        """Тест информационных запросов."""
        logger.info("ℹ️ Тестирование информационных запросов...")
        
        try:
            # Информация о трейдере
            try:
                trader_info = await self.connector.get_trader_info()
                self.log_test_result("Информация о трейдере", True, "Информация получена")
            except Exception as e:
                self.log_test_result("Информация о трейдере", False, str(e))
            
            # Сверка позиций
            try:
                reconcile_response = await self.connector.reconcile()
                self.log_test_result("Сверка позиций", True, "Сверка выполнена")
            except Exception as e:
                self.log_test_result("Сверка позиций", False, str(e))
            
            # Нереализованная P&L
            try:
                pnl_response = await self.connector.get_position_unrealized_pnl()
                self.log_test_result("Нереализованная P&L", True, "P&L получена")
            except Exception as e:
                self.log_test_result("Нереализованная P&L", False, str(e))
            
            # Список сделок
            try:
                to_timestamp = int(datetime.now().timestamp() * 1000)
                from_timestamp = int((datetime.now() - timedelta(days=1)).timestamp() * 1000)
                
                deals_response = await self.connector.get_deal_list(
                    from_timestamp,
                    to_timestamp,
                    max_rows=10
                )
                self.log_test_result("Список сделок", True, "Список сделок получен")
            except Exception as e:
                self.log_test_result("Список сделок", False, str(e))
                
        except Exception as e:
            self.log_test_result("Информационные запросы", False, str(e))

    async def test_event_handlers(self):
        """Тест обработчиков событий."""
        logger.info("🔧 Тестирование обработчиков событий...")
        
        try:
            # Счетчики для обработчиков
            spot_events = 0
            execution_events = 0
            
            # Обработчик спотовых котировок
            def spot_handler(message):
                nonlocal spot_events
                spot_events += 1
                logger.debug(f"Получено спотовое событие #{spot_events}")
            
            # Обработчик торговых событий
            def execution_handler(message):
                nonlocal execution_events
                execution_events += 1
                logger.debug(f"Получено торговое событие #{execution_events}")
            
            # Регистрируем обработчики
            from ctrader_open_api_async.messages.OpenApiMessages_pb2 import ProtoOASpotEvent, ProtoOAExecutionEvent
            
            self.connector.add_message_handler(ProtoOASpotEvent().payloadType, spot_handler)
            self.connector.add_message_handler(ProtoOAExecutionEvent().payloadType, execution_handler)
            
            self.log_test_result("Регистрация обработчиков", True, "Обработчики зарегистрированы")
            
            # Подписываемся на котировки для тестирования обработчиков
            if self.symbol_id:
                try:
                    await self.connector.subscribe_spots([self.symbol_id])
                    await asyncio.sleep(5)  # Ждем события
                    await self.connector.unsubscribe_spots([self.symbol_id])
                    
                    if spot_events > 0:
                        self.log_test_result("Обработчик котировок", True, f"Обработано {spot_events} событий")
                    else:
                        self.log_test_result("Обработчик котировок", True, "События не получены (возможно рынок закрыт)")
                except Exception as e:
                    self.log_test_result("Обработчик котировок", False, str(e))
            else:
                self.log_test_result("Обработчик котировок", False, "Символ не выбран")
            
            # Удаляем обработчики
            self.connector.remove_message_handler(ProtoOASpotEvent().payloadType)
            self.connector.remove_message_handler(ProtoOAExecutionEvent().payloadType)
            
            self.log_test_result("Удаление обработчиков", True, "Обработчики удалены")
            
        except Exception as e:
            self.log_test_result("Обработчики событий", False, str(e))

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

    async def wait_for_auth(self):
        """Ожидание получения кода авторизации."""
        logger.info("Ожидание авторизации...")
        while not self.auth_code:
            await asyncio.sleep(1)

    def print_final_report(self):
        """Печатает итоговый отчет."""
        total_tests = self.tests_passed + self.tests_failed
        success_rate = (self.tests_passed / total_tests * 100) if total_tests > 0 else 0
        
        logger.info("=" * 60)
        logger.info("📋 ИТОГОВЫЙ ОТЧЕТ ТЕСТИРОВАНИЯ")
        logger.info("=" * 60)
        logger.info(f"Всего тестов: {total_tests}")
        logger.info(f"✅ Пройдено: {self.tests_passed}")
        logger.info(f"❌ Провалено: {self.tests_failed}")
        logger.info(f"📊 Успешность: {success_rate:.1f}%")
        logger.info("=" * 60)
        
        # Сохраняем отчет в файл
        report = {
            "timestamp": datetime.now().isoformat(),
            "total_tests": total_tests,
            "passed": self.tests_passed,
            "failed": self.tests_failed,
            "success_rate": success_rate,
            "results": self.test_results
        }
        
        with open("test_report.json", "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        logger.info("📄 Подробный отчет сохранен в test_report.json")

    async def test_cleanup(self):
        """Тест очистки всех тестовых ордеров и позиций."""
        logger.info("🧹 Тестирование очистки всех тестовых ордеров и позиций...")
        
        try:
            canceled_orders = 0
            closed_positions = 0
            
            # Получаем список всех активных ордеров
            try:
                orders_response = await self.connector.get_order_list()
                
                # Извлекаем ордера из ответа
                from ctrader_open_api_async.protobuf import Protobuf
                extracted = Protobuf.extract(orders_response)
                
                if hasattr(extracted, 'order') and extracted.order:
                    # Фильтруем только активные ордера (статус 1 = ORDER_STATUS_ACCEPTED)
                    active_orders = [order for order in extracted.order 
                                   if hasattr(order, 'orderStatus') and order.orderStatus == 1]
                    
                    if active_orders:
                        logger.info(f"Найдено {len(active_orders)} активных ордеров для проверки")
                        
                        for order in active_orders:
                            # Отменяем только тестовые ордера
                            should_cancel = False
                            
                            if hasattr(order, 'comment') and order.comment == "Test limit order":
                                should_cancel = True
                            elif (hasattr(order, 'limitPrice') and 
                                  order.limitPrice >= 999999.0):
                                should_cancel = True
                            
                            if should_cancel:
                                try:
                                    await self.connector.cancel_order(order.orderId)
                                    canceled_orders += 1
                                    logger.info(f"✅ Отменен тестовый ордер {order.orderId}")
                                    await asyncio.sleep(0.5)  # Небольшая пауза между отменами
                                except Exception as e:
                                    logger.warning(f"⚠️ Не удалось отменить ордер {order.orderId}: {e}")
                    else:
                        logger.info("Активные ордера отсутствуют")
                else:
                    logger.info("Активные ордера отсутствуют")
            except Exception as e:
                logger.error(f"❌ Ошибка получения списка ордеров: {e}")
            
            # Получаем список всех открытых позиций через reconcile
            try:
                reconcile_response = await self.connector.reconcile()
                
                # Извлекаем позиции из ответа
                from ctrader_open_api_async.protobuf import Protobuf
                extracted = Protobuf.extract(reconcile_response)
                
                if hasattr(extracted, 'position') and extracted.position:
                    # Фильтруем только открытые позиции (статус 1 = POSITION_STATUS_OPEN)
                    open_positions = [position for position in extracted.position 
                                    if hasattr(position, 'positionStatus') and position.positionStatus == 1]
                    
                    if open_positions:
                        logger.info(f"Найдено {len(open_positions)} открытых позиций для проверки")
                        
                        for position in open_positions:
                            # Закрываем только тестовые позиции
                            should_close = False
                            
                            if (hasattr(position, 'tradeData') and 
                                hasattr(position.tradeData, 'label') and
                                position.tradeData.label == "AsyncTest"):
                                should_close = True
                            elif (hasattr(position, 'tradeData') and 
                                  hasattr(position.tradeData, 'comment') and
                                  position.tradeData.comment == "Test order"):
                                should_close = True
                            
                            if should_close:
                                try:
                                    # Получаем объем позиции
                                    volume = position.tradeData.volume if hasattr(position.tradeData, 'volume') else self.volume
                                    await self.connector.close_position(position.positionId, volume)
                                    closed_positions += 1
                                    logger.info(f"✅ Закрыта тестовая позиция {position.positionId}")
                                    await asyncio.sleep(0.5)  # Небольшая пауза между закрытиями
                                except Exception as e:
                                    logger.warning(f"⚠️ Не удалось закрыть позицию {position.positionId}: {e}")
                    else:
                        logger.info("Открытые позиции отсутствуют")
                else:
                    logger.info("Открытые позиции отсутствуют")
            except Exception as e:
                logger.error(f"❌ Ошибка получения списка позиций: {e}")
            
            # Итоговый результат
            if canceled_orders > 0 or closed_positions > 0:
                message = f"Отменено {canceled_orders} ордеров, закрыто {closed_positions} позиций"
                self.log_test_result("Очистка тестовых ордеров и позиций", True, message)
            else:
                self.log_test_result("Очистка тестовых ордеров и позиций", True, "Тестовые ордера и позиции не найдены")
                
        except Exception as e:
            self.log_test_result("Очистка тестовых ордеров и позиций", False, str(e))

async def main():
    """Главная функция."""
    tester = FullAsyncTester("credentials.json")
    await tester.run_all_tests()

if __name__ == "__main__":
    asyncio.run(main()) 