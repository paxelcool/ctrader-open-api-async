#!/usr/bin/env python3
"""Упрощенный пример OAuth авторизации для cTrader Open API Async."""

import asyncio
import logging
from typing import Optional

from ctrader_open_api_async import AsyncClient, AsyncAuth, EndPoints
from ctrader_open_api_async.messages.OpenApiMessages_pb2 import *

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def get_access_token_manual(client_id: str, client_secret: str, redirect_uri: str) -> Optional[str]:
    """Получение access token через ручной ввод кода авторизации.
    
    Args:
        client_id: ID приложения
        client_secret: Секрет приложения
        redirect_uri: URI для редиректа
        
    Returns:
        Access token или None при ошибке
    """
    async with AsyncAuth(client_id, client_secret, redirect_uri) as auth:
        # 1. Получаем URL для авторизации
        auth_url = auth.get_auth_uri(scope="trading")
        
        print(f"\n🔗 Перейдите по ссылке для авторизации:")
        print(f"{auth_url}")
        print(f"\n📋 Инструкция:")
        print(f"1. Откройте ссылку выше в браузере")
        print(f"2. Войдите в ваш cTrader ID аккаунт")
        print(f"3. Разрешите доступ приложению")
        print(f"4. Скопируйте код авторизации из URL редиректа")
        print(f"   (параметр 'code' в адресной строке)")
        
        # 2. Ждем ввод кода от пользователя
        auth_code = input("\n🔑 Введите код авторизации: ").strip()
        
        if not auth_code:
            print("❌ Код авторизации не введен")
            return None
        
        try:
            # 3. Обмениваем код на токен
            token_data = await auth.get_token(auth_code)
            access_token = token_data['access_token']
            
            print(f"✅ Access token получен!")
            print(f"📝 Сохраните токен для будущего использования:")
            print(f"   {access_token}")
            
            return access_token
            
        except Exception as e:
            print(f"❌ Ошибка получения токена: {e}")
            return None


async def main():
    """Основная функция упрощенного примера."""
    
    # НАСТРОЙКИ - замените на ваши данные
    CLIENT_ID = "your_client_id"
    CLIENT_SECRET = "your_client_secret" 
    REDIRECT_URI = "http://localhost:8080/auth/callback"
    IS_LIVE = False  # True для live, False для demo
    
    # Можете указать уже полученный access token для пропуска OAuth
    EXISTING_ACCESS_TOKEN = None  # "your_existing_access_token"
    
    if CLIENT_ID == "your_client_id":
        print("❌ ОШИБКА: Укажите ваши CLIENT_ID и CLIENT_SECRET")
        print("\n📋 Инструкция по настройке:")
        print("1. Зайдите на https://id.ctrader.com/")
        print("2. Создайте приложение в разделе 'Applications'")
        print("3. Добавьте redirect URI: http://localhost:8080/auth/callback")
        print("4. Скопируйте Client ID и Client Secret")
        return
    
    try:
        # Шаг 1: Получаем access token
        if EXISTING_ACCESS_TOKEN:
            access_token = EXISTING_ACCESS_TOKEN
            print("🔑 Используется существующий access token")
        else:
            print("🔐 Выполнение OAuth авторизации...")
            access_token = await get_access_token_manual(CLIENT_ID, CLIENT_SECRET, REDIRECT_URI)
            if not access_token:
                return
        
        # Шаг 2: Подключаемся к API
        host = EndPoints.PROTOBUF_LIVE_HOST if IS_LIVE else EndPoints.PROTOBUF_DEMO_HOST
        
        async with AsyncClient(host, EndPoints.PROTOBUF_PORT) as client:
            print("🌐 Подключение к cTrader Open API...")
            
            # Аутентификация приложения
            await client.send_application_auth_req(CLIENT_ID, CLIENT_SECRET)
            print("✅ Аутентификация приложения успешна")
            
            # Получение аккаунтов
            accounts_response = await client.send_get_account_list_by_access_token_req(access_token)
            accounts = list(accounts_response.ctidTraderAccount)
            
            if not accounts:
                print("❌ Не найдено аккаунтов")
                return
            
            account_id = accounts[0].ctidTraderAccountId
            print(f"📊 Найдено аккаунтов: {len(accounts)}, используется ID: {account_id}")
            
            # Авторизация торгового аккаунта
            await client.send_account_auth_req(account_id, access_token)
            print("✅ Авторизация торгового аккаунта успешна")
            
            # Получение информации о трейдере
            trader_response = await client.send_trader_req(account_id)
            trader = trader_response.trader
            
            print(f"\n📈 Информация о счете:")
            print(f"   Баланс: {trader.balance / (10 ** trader.moneyDigits):.2f}")
            print(f"   Используемая маржа: {trader.totalMarginUsed / (10 ** trader.moneyDigits):.2f}")
            print(f"   Нереализованная P&L: {trader.totalUnrealizedGrossPnL / (10 ** trader.moneyDigits):.2f}")
            
            # Получение символов
            symbols_response = await client.send_symbols_list_req(account_id)
            symbols = list(symbols_response.symbol)
            
            print(f"\n📋 Доступные символы (первые 5 из {len(symbols)}):")
            for i, symbol in enumerate(symbols[:5]):
                print(f"   {i+1}. {symbol.symbolName} (ID: {symbol.symbolId})")
            
            print(f"\n🎉 Подключение успешно! Теперь можно выполнять торговые операции.")
            
    except Exception as e:
        logger.error(f"Ошибка: {e}")
        print(f"❌ Произошла ошибка: {e}")


if __name__ == "__main__":
    print("cTrader Open API - Упрощенный OAuth пример")
    print("=" * 45)
    asyncio.run(main()) 