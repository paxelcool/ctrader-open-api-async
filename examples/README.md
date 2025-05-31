# Примеры использования cTrader Open API Async

Эта директория содержит примеры использования библиотеки cTrader Open API Async.

## 📋 Список примеров

### 🚀 [basic_usage.py](basic_usage.py)

Базовый пример, демонстрирующий:

- Подключение к API
- Аутентификацию приложения
- Получение списка аккаунтов
- Получение списка символов
- Подписку на спот цены
- Прослушивание событий

## 🔧 Подготовка к запуску

### 1. Установка библиотеки

```bash
pip install ctrader-open-api-async
```

### 2. Получение учетных данных

Для работы с примерами вам понадобятся:

- **Client ID** - ID вашего приложения
- **Client Secret** - Секрет вашего приложения  
- **Access Token** - Токен доступа к аккаунту

Получить их можно в [cTrader Developer Portal](https://ctrader.com/developer).

### 3. Настройка примеров

Откройте файл примера и замените следующие значения:

```python
CLIENT_ID = "your_client_id"          # Ваш Client ID
CLIENT_SECRET = "your_client_secret"  # Ваш Client Secret
ACCESS_TOKEN = "your_access_token"    # Ваш Access Token
IS_LIVE = False                       # True для live, False для demo
```

## 🚀 Запуск примеров

### Базовый пример

```bash
python examples/basic_usage.py
```

## 📖 Что демонстрируют примеры

### Подключение и аутентификация

```python
# Создание клиента
client = AsyncClient(host, port)

# Подключение
await client.connect()

# Аутентификация
auth_request = ProtoOAApplicationAuthReq()
auth_request.clientId = client_id
auth_request.clientSecret = client_secret
response = await client.send_request(auth_request)
```

### Получение данных

```python
# Получение аккаунтов
accounts_request = ProtoOAGetAccountListByAccessTokenReq()
accounts_request.accessToken = access_token
accounts = await client.send_request(accounts_request)

# Получение символов
symbols_request = ProtoOASymbolsListReq()
symbols_request.ctidTraderAccountId = account_id
symbols = await client.send_request(symbols_request)
```

### Подписка на события

```python
# Подписка на спот цены
spots_request = ProtoOASubscribeSpotsReq()
spots_request.ctidTraderAccountId = account_id
spots_request.symbolId.extend(symbol_ids)
await client.send_request(spots_request)

# Прослушивание событий
async for message in client.message_stream():
    if message.payloadType == ProtoOAPayloadType.PROTO_OA_SPOT_EVENT:
        spot_event = ProtoOASpotEvent()
        spot_event.ParseFromString(message.payload)
        print(f"Новая цена: {spot_event}")
```

## 🔍 Отладка

Для включения подробного логирования добавьте в начало скрипта:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## ⚠️ Важные замечания

1. **Безопасность**: Никогда не коммитьте ваши реальные учетные данные в git
2. **Demo vs Live**: Всегда начинайте тестирование с demo сервера
3. **Rate Limits**: Соблюдайте ограничения API на количество запросов
4. **Обработка ошибок**: В production коде всегда обрабатывайте исключения

## 📞 Поддержка

Если у вас возникли вопросы по примерам:

- 📖 Изучите [основную документацию](../README.md)
- 🐛 [Создайте issue](https://github.com/paxelcool/ctrader-open-api-async/issues)
- 💬 Обратитесь к [cTrader API документации](https://help.ctrader.com/open-api/)

## 🔗 Полезные ссылки

- [cTrader Developer Portal](https://ctrader.com/developer)
- [cTrader Open API Documentation](https://help.ctrader.com/open-api/)
- [Protobuf Messages Reference](https://help.ctrader.com/open-api/messages/)
