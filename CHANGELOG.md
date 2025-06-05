# Changelog

Все значимые изменения в этом проекте будут документированы в этом файле.

Формат основан на [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
и этот проект придерживается [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.0.1] - 2025-01-31

### Добавлено

- 🔐 **Полная поддержка OAuth 2.0** согласно официальной документации cTrader
- 📝 **Новые примеры OAuth авторизации**:
  - `oauth_auth_example.py` - полный автоматический пример с локальным HTTP сервером
  - `simple_oauth_example.py` - упрощенный пример с ручным вводом кода
- 📚 **Подробное руководство по OAuth** (`OAuth_GUIDE.md`)
- 🔧 **Класс AsyncAuth** для работы с OAuth токенами
- ⚠️ **Предупреждения в устаревших примерах** с рекомендациями по миграции

### Изменено

- 📖 **Обновлена документация** с описанием правильного OAuth потока
- 🔄 **Исправлены примеры** для соответствия официальным требованиям API
- 📋 **Обновлено README** с подробным описанием OAuth процесса
- 🎯 **Улучшена структура примеров** с пояснениями и инструкциями

### Исправлено

- ❌ **Устранена проблема с отсутствием OAuth редиректа** в примерах
- 🔗 **Исправлены неточности в описании** процесса авторизации
- 📱 **Добавлена поддержка локального HTTP сервера** для обработки OAuth редиректа

### Особенности OAuth реализации

- **Автоматический запуск локального сервера** на порту 8080 для обработки редиректа
- **Открытие браузера** для авторизации пользователя
- **Обмен authorization code на access token** согласно спецификации OAuth 2.0
- **Поддержка refresh token** для обновления истекших токенов
- **Валидация токенов** и обработка ошибок
- **Безопасное хранение секретов** с рекомендациями по использованию переменных окружения

## [2.0.0] - 2025-01-31

### Добавлено

- 🚀 Полная переработка с использованием async/await вместо Twisted
- 📦 Поддержка установки через pip
- 🛡️ Полная типизация с type hints
- 🧪 Тесты с pytest-asyncio
- 📚 Подробная документация и примеры
- 🔧 Современная конфигурация проекта (pyproject.toml)
- 📋 Поддержка Python 3.8+

### Изменено

- ⚡ Замена Twisted на asyncio для лучшей производительности
- 🔄 Упрощенный API с async/await синтаксисом
- 📝 Обновленная документация с примерами

### Удалено

- ❌ Зависимость от Twisted
- ❌ Устаревшие callback-based методы

## [1.x.x] - Оригинальная версия

Базируется на оригинальной библиотеке [OpenApiPy](https://github.com/spotware/OpenApiPy) от Spotware.

### Особенности оригинальной версии

- Использование Twisted framework
- Callback-based архитектура
- Поддержка всех функций cTrader Open API

## 📝 Примечания по миграции

### С версии 1.x на 2.0.x

1. **OAuth обязателен** - необходимо реализовать полный OAuth 2.0 поток
2. **Новые методы API** - используйте методы `send_*_req` вместо создания сообщений вручную
3. **Async context managers** - рекомендуется использовать `async with` для автоматического управления ресурсами
4. **Типизация** - добавлены type hints для лучшей поддержки IDE

### Пример миграции

**Старый код (v1.x):**
```python
# Без OAuth, с Twisted
client = OpenClient(host, port)
client.connect()
auth_req = ProtoOAApplicationAuthReq()
auth_req.clientId = client_id
client.send(auth_req)
```

**Новый код (v2.0+):**
```python
# С OAuth и async/await
async with AsyncAuth(client_id, client_secret, redirect_uri) as auth:
    access_token = await auth.get_token(auth_code)

async with AsyncClient(host, port) as client:
    await client.send_application_auth_req(client_id, client_secret)
    accounts = await client.send_get_account_list_by_access_token_req(access_token)
```
