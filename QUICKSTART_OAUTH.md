# 🚀 Быстрый старт OAuth для cTrader Open API

Это краткое руководство поможет вам быстро настроить OAuth авторизацию для cTrader Open API.

## 📋 Что вам понадобится

1. **Аккаунт cTrader ID** - [зарегистрируйтесь здесь](https://id.ctrader.com/)
2. **Python 3.8+** - убедитесь, что Python установлен
3. **10 минут времени** - для настройки и первого запуска

## ⚡ Быстрая настройка (5 шагов)

### Шаг 1: Установка библиотеки

```bash
pip install ctrader-open-api-async
```

### Шаг 2: Создание приложения в cTrader

1. Откройте [cTrader ID Portal](https://id.ctrader.com/)
2. Войдите в аккаунт → раздел **"Applications"** → **"Create New Application"**
3. Заполните:
   - **Name**: `My Trading App`
   - **Type**: `Desktop Application`
   - **Redirect URI**: `http://localhost:8080/auth/callback`
4. Сохраните **Client ID** и **Client Secret**

### Шаг 3: Скачивание примера

```bash
# Скачайте простой пример
curl -O https://raw.githubusercontent.com/paxelcool/ctrader-open-api-async/main/examples/simple_oauth_example.py
```

Или создайте файл `quick_start.py`:

```python
#!/usr/bin/env python3
import asyncio
from ctrader_open_api_async import AsyncClient, AsyncAuth, EndPoints

async def main():
    # 📝 ЗАМЕНИТЕ НА ВАШИ ДАННЫЕ
    CLIENT_ID = "your_client_id"
    CLIENT_SECRET = "your_client_secret"
    REDIRECT_URI = "http://localhost:8080/auth/callback"
    
    # 1️⃣ OAuth авторизация
    async with AsyncAuth(CLIENT_ID, CLIENT_SECRET, REDIRECT_URI) as auth:
        auth_url = auth.get_auth_uri(scope="trading")
        print(f"🔗 Откройте в браузере: {auth_url}")
        auth_code = input("🔑 Введите код из URL: ")
        token_data = await auth.get_token(auth_code)
        access_token = token_data['access_token']
        print("✅ Токен получен!")
    
    # 2️⃣ Подключение к API
    async with AsyncClient(EndPoints.PROTOBUF_DEMO_HOST, EndPoints.PROTOBUF_PORT) as client:
        await client.send_application_auth_req(CLIENT_ID, CLIENT_SECRET)
        
        # Получение аккаунтов
        accounts_response = await client.send_get_account_list_by_access_token_req(access_token)
        accounts = list(accounts_response.ctidTraderAccount)
        account_id = accounts[0].ctidTraderAccountId
        
        # Авторизация аккаунта
        await client.send_account_auth_req(account_id, access_token)
        
        # Получение информации
        trader_response = await client.send_trader_req(account_id)
        balance = trader_response.trader.balance / (10 ** trader_response.trader.moneyDigits)
        
        print(f"🎉 Подключено! Баланс: {balance:.2f}")

if __name__ == "__main__":
    asyncio.run(main())
```

### Шаг 4: Настройка учетных данных

Замените в коде:
```python
CLIENT_ID = "your_client_id"      # Ваш Client ID
CLIENT_SECRET = "your_client_secret"  # Ваш Client Secret
```

### Шаг 5: Запуск

```bash
python quick_start.py
```

## 🎯 Что произойдет

1. **Откроется ссылка** для авторизации в браузере
2. **Войдите в cTrader ID** и разрешите доступ
3. **Скопируйте код** из адресной строки после редиректа
4. **Вставьте код** в консоль
5. **Получите токен** и подключитесь к API! 🎉

## 📱 Автоматический пример (рекомендуется)

Для автоматической обработки редиректа используйте:

```bash
python examples/oauth_auth_example.py
```

Этот пример:
- ✅ Автоматически запускает локальный сервер
- ✅ Открывает браузер для авторизации  
- ✅ Автоматически получает код авторизации
- ✅ Выполняет все операции с API

## 🆘 Частые проблемы

### ❌ "Invalid redirect URI"
**Решение**: Убедитесь, что в настройках приложения указан точно `http://localhost:8080/auth/callback`

### ❌ "Invalid client credentials"  
**Решение**: Проверьте правильность Client ID и Client Secret (без лишних пробелов)

### ❌ "Authorization code expired"
**Решение**: Код действует 1 минуту - получите новый, перейдя по ссылке снова

## 📚 Дополнительные ресурсы

- 📖 [Полное руководство по OAuth](OAuth_GUIDE.md)
- 🔍 [Примеры в папке examples/](examples/)
- 🌐 [Официальная документация](https://help.ctrader.com/open-api/account-authentication/)

## 🔐 Безопасность

**Для продакшн используйте:**
```python
import os
CLIENT_ID = os.getenv('CTRADER_CLIENT_ID')
CLIENT_SECRET = os.getenv('CTRADER_CLIENT_SECRET')
```

**Никогда не коммитьте секреты в Git!**

---

**Время на настройку**: ~5-10 минут  
**Сложность**: Начинающий  
**Поддержка**: [GitHub Issues](https://github.com/paxelcool/ctrader-open-api-async/issues) 