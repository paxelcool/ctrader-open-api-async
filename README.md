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

## 🚀 Быстрый старт

```python
import asyncio
from ctrader_open_api_async import AsyncClient, EndPoints
from ctrader_open_api_async.messages.OpenApiCommonMessages_pb2 import *
from ctrader_open_api_async.messages.OpenApiMessages_pb2 import *

async def main():
    # Выбор хоста (Live или Demo)
    host_type = "demo"  # или "live"
    host = EndPoints.PROTOBUF_LIVE_HOST if host_type == "live" else EndPoints.PROTOBUF_DEMO_HOST
    
    # Создание клиента
    client = AsyncClient(host, EndPoints.PROTOBUF_PORT)
    
    try:
        # Подключение
        await client.connect()
        print("Подключено к cTrader Open API")
        
        # Аутентификация приложения
        auth_request = ProtoOAApplicationAuthReq()
        auth_request.clientId = "your_client_id"
        auth_request.clientSecret = "your_client_secret"
        
        response = await client.send_request(auth_request)
        print(f"Аутентификация успешна: {response}")
        
        # Получение аккаунтов
        accounts_request = ProtoOAGetAccountListByAccessTokenReq()
        accounts_request.accessToken = "your_access_token"
        
        accounts_response = await client.send_request(accounts_request)
        print(f"Аккаунты: {accounts_response}")
        
    except Exception as e:
        print(f"Ошибка: {e}")
    finally:
        await client.disconnect()

if __name__ == "__main__":
    asyncio.run(main())
```

## 📖 Документация

### Основные классы

#### AsyncClient
Основной класс для взаимодействия с API:

```python
from ctrader_open_api_async import AsyncClient

client = AsyncClient(host, port)
await client.connect()
response = await client.send_request(request)
await client.disconnect()
```

#### Protobuf
Утилиты для работы с protobuf сообщениями:

```python
from ctrader_open_api_async import Protobuf

# Извлечение данных из сообщения
data = Protobuf.extract(message)

# Создание сообщения
message = Protobuf.create_message(message_type, **kwargs)
```

### Примеры использования

#### Получение символов
```python
async def get_symbols(client, account_id):
    request = ProtoOASymbolsListReq()
    request.ctidTraderAccountId = account_id
    
    response = await client.send_request(request)
    return response.symbol
```

#### Размещение ордера
```python
async def place_order(client, account_id, symbol_id, volume, order_type):
    request = ProtoOANewOrderReq()
    request.ctidTraderAccountId = account_id
    request.symbolId = symbol_id
    request.orderType = order_type
    request.tradeSide = ProtoOATradeSide.BUY
    request.volume = volume
    
    response = await client.send_request(request)
    return response
```

#### Подписка на события
```python
async def subscribe_to_spots(client, account_id, symbol_ids):
    request = ProtoOASubscribeSpotsReq()
    request.ctidTraderAccountId = account_id
    request.symbolId.extend(symbol_ids)
    
    await client.send_request(request)
    
    # Обработка входящих сообщений
    async for message in client.message_stream():
        if message.payloadType == ProtoOAPayloadType.PROTO_OA_SPOT_EVENT:
            spot_event = ProtoOASpotEvent()
            spot_event.ParseFromString(message.payload)
            print(f"Новая цена: {spot_event}")
```

## 🔧 Разработка

### Настройка окружения
```bash
git clone https://github.com/yourusername/ctrader-open-api-async.git
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

- 🐛 [Сообщить об ошибке](https://github.com/yourusername/ctrader-open-api-async/issues)
- 💡 [Предложить улучшение](https://github.com/yourusername/ctrader-open-api-async/issues)
- 📖 [Документация](https://github.com/yourusername/ctrader-open-api-async/blob/main/README.md)

## 🔗 Полезные ссылки

- [cTrader Open API Documentation](https://help.ctrader.com/open-api/)
- [Оригинальная библиотека OpenApiPy](https://github.com/spotware/OpenApiPy)
- [Python asyncio документация](https://docs.python.org/3/library/asyncio.html) 