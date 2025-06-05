# cTrader Open API Async

[![PyPI version](https://badge.fury.io/py/ctrader-open-api-async.svg)](https://badge.fury.io/py/ctrader-open-api-async)
[![Python versions](https://img.shields.io/pypi/pyversions/ctrader-open-api-async.svg)](https://pypi.org/project/ctrader-open-api-async/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Async/await версия Python библиотеки для взаимодействия с cTrader Open API.

Этот пакет является форком оригинального [OpenApiPy](https://github.com/spotware/OpenApiPy), переписанным с использованием современного async/await синтаксиса вместо Twisted.

## ✨ Особенности

- 🚀 **Современный async/await синтаксис** - никакого Twisted, только чистый asyncio
- 📦 **Простая установка** - доступен через pip
- 🔄 **Полная совместимость** - поддерживает все функции оригинального API
- 🛡️ **Типизация** - полная поддержка type hints
- 🔐 **OAuth авторизация** - полная поддержка OAuth 2.0 потока согласно документации cTrader
- 📚 **Подробная документация** - примеры и руководства
- 🧪 **Тестирование** - покрыт тестами с pytest-asyncio

## 📦 Установка

```bash
pip install ctrader-open-api-async
```

Для разработки:

```bash
pip install ctrader-open-api-async[dev]
```

## 🔐 OAuth авторизация

⚠️ **ВАЖНО**: Начиная с версии 2.0.0, библиотека полностью поддерживает OAuth 2.0 авторизацию согласно [официальной документации cTrader](https://help.ctrader.com/open-api/account-authentication/).

### Настройка приложения

1. Зайдите на [cTrader ID Portal](https://id.ctrader.com/)
2. Создайте новое приложение в разделе "Applications"
3. Добавьте redirect URI: `http://localhost:8080/auth/callback` (для локальной разработки)
4. Скопируйте Client ID и Client Secret

### Полный пример OAuth авторизации

```python
import asyncio
from ctrader_open_api_async import AsyncClient, AsyncAuth, EndPoints

async def oauth_example():
    # Настройки OAuth
    CLIENT_ID = "your_client_id"
    CLIENT_SECRET = "your_client_secret"
    REDIRECT_URI = "http://localhost:8080/auth/callback"
    
    # 1. OAuth авторизация
    async with AsyncAuth(CLIENT_ID, CLIENT_SECRET, REDIRECT_URI) as auth:
        # Получаем URL для авторизации
        auth_url = auth.get_auth_uri(scope="trading")
        print(f"Перейдите по ссылке: {auth_url}")
        
        # Пользователь авторизуется и вводит код
        auth_code = input("Введите код авторизации: ")
        
        # Обмениваем код на токен
        token_data = await auth.get_token(auth_code)
        access_token = token_data['access_token']
    
    # 2. Подключение к API
    host = EndPoints.PROTOBUF_DEMO_HOST  # или PROTOBUF_LIVE_HOST
    
    async with AsyncClient(host, EndPoints.PROTOBUF_PORT) as client:
        # Аутентификация приложения
        await client.send_application_auth_req(CLIENT_ID, CLIENT_SECRET)
        
        # Получение аккаунтов
        accounts_response = await client.send_get_account_list_by_access_token_req(access_token)
        accounts = list(accounts_response.ctidTraderAccount)
        
        # Авторизация торгового аккаунта
        account_id = accounts[0].ctidTraderAccountId
        await client.send_account_auth_req(account_id, access_token)
        
        # Получение информации о трейдере
        trader_response = await client.send_trader_req(account_id)
        print(f"Баланс: {trader_response.trader.balance}")

if __name__ == "__main__":
    asyncio.run(oauth_example())
```

## 🚀 Быстрый старт

Для полного понимания OAuth процесса смотрите примеры в папке `examples/`:

- `oauth_auth_example.py` - полный автоматический пример с локальным сервером
- `simple_oauth_example.py` - упрощенный пример с ручным вводом кода

## 📖 Документация

### Основные классы

#### AsyncClient

Основной класс для взаимодействия с API:

```python
from ctrader_open_api_async import AsyncClient

async with AsyncClient(host, port) as client:
    response = await client.send_application_auth_req(client_id, client_secret)
    # ... другие операции
```

#### AsyncAuth

Класс для OAuth авторизации:

```python
from ctrader_open_api_async import AsyncAuth

async with AsyncAuth(client_id, client_secret, redirect_uri) as auth:
    auth_url = auth.get_auth_uri(scope="trading")
    token_data = await auth.get_token(auth_code)
    access_token = token_data['access_token']
```

### Примеры использования

#### Получение символов

```python
async def get_symbols(client, account_id):
    response = await client.send_symbols_list_req(account_id)
    return list(response.symbol)
```

#### Размещение ордера

```python
async def place_order(client, account_id, symbol_id, volume):
    response = await client.send_new_order_req(
        ctid_trader_account_id=account_id,
        symbol_id=symbol_id,
        order_type=ProtoOAOrderType.MARKET,
        trade_side=ProtoOATradeSide.BUY,
        volume=volume
    )
    return response
```

#### Подписка на спотовые цены

```python
async def subscribe_to_spots(client, account_id, symbol_ids):
    # Подписка
    await client.send_subscribe_spots_req(account_id, symbol_ids)
    
    # Установка обработчика сообщений
    def on_message(client, message):
        if hasattr(message, 'payload') and message.payloadType == ProtoOAPayloadType.PROTO_OA_SPOT_EVENT:
            # Обработка спотовой цены
            print(f"Новая цена: {message}")
    
    client.set_message_received_callback(on_message)
```

## 🔧 Разработка

### Настройка окружения

```bash
git clone https://github.com/paxelcool/ctrader-open-api-async.git
cd ctrader-open-api-async
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# или
.venv\Scripts\activate  # Windows
pip install -e .[dev]
```

### Запуск тестов

```bash
pytest
```

### Форматирование кода

```bash
black .
ruff check .
```

### Проверка типов

```bash
mypy ctrader_open_api_async
```

## 🔐 OAuth процесс согласно документации

Согласно [официальной документации cTrader](https://help.ctrader.com/open-api/account-authentication/), процесс авторизации включает:

### 1. Получение authorization code

Пользователь перенаправляется на:
```
https://openapi.ctrader.com/apps/auth?client_id={CLIENT_ID}&redirect_uri={REDIRECT_URI}&response_type=code&scope={SCOPE}
```

### 2. Обмен кода на access token

POST запрос к `https://openapi.ctrader.com/apps/token` с параметрами:
- `grant_type=authorization_code`
- `code={AUTHORIZATION_CODE}`
- `redirect_uri={REDIRECT_URI}`
- `client_id={CLIENT_ID}`
- `client_secret={CLIENT_SECRET}`

### 3. Использование access token

- `ProtoOAApplicationAuthReq` - аутентификация приложения
- `ProtoOAGetAccountListByAccessTokenReq` - получение списка аккаунтов
- `ProtoOAAccountAuthReq` - авторизация торгового аккаунта

## ⚠️ Миграция с версии 1.x

Если вы используете версию 1.x, обратите внимание на изменения:

1. **OAuth обязателен** - теперь нужно проходить полный OAuth поток
2. **Новые методы API** - используйте методы `send_*_req` вместо создания сообщений вручную
3. **Async context managers** - рекомендуется использовать `async with`

## 🤝 Вклад в проект

Мы приветствуем вклад в развитие проекта! Пожалуйста:

1. Форкните репозиторий
2. Создайте ветку для новой функции (`git checkout -b feature/amazing-feature`)
3. Зафиксируйте изменения (`git commit -m 'Add amazing feature'`)
4. Отправьте в ветку (`git push origin feature/amazing-feature`)
5. Откройте Pull Request

## 📋 Требования

- Python 3.8+
- aiohttp
- websockets
- protobuf
- cryptography

## 📄 Лицензия

Этот проект лицензирован под MIT License - см. файл [LICENSE](LICENSE) для деталей.

## 🙏 Благодарности

- [Spotware](https://github.com/spotware) за оригинальную библиотеку [OpenApiPy](https://github.com/spotware/OpenApiPy)
- Сообщество Python за отличные async/await инструменты

## 📞 Поддержка

- 🐛 [Сообщить об ошибке](https://github.com/paxelcool/ctrader-open-api-async/issues)
- 💡 [Предложить улучшение](https://github.com/paxelcool/ctrader-open-api-async/issues)
- 📖 [Документация](https://github.com/paxelcool/ctrader-open-api-async/blob/main/README.md)
- 🔍 [Примеры OAuth](https://github.com/paxelcool/ctrader-open-api-async/tree/main/examples)

## 🔗 Полезные ссылки

- [cTrader Open API Documentation](https://help.ctrader.com/open-api/)
- [cTrader ID Portal](https://id.ctrader.com/) (для создания приложений)
- [OAuth 2.0 Authentication Flow](https://help.ctrader.com/open-api/account-authentication/)
- [Оригинальная библиотека OpenApiPy](https://github.com/spotware/OpenApiPy)
- [Python asyncio документация](https://docs.python.org/3/library/asyncio.html)
