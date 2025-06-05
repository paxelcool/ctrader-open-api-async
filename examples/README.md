# Примеры использования cTrader Open API Async

Эта папка содержит примеры использования библиотеки cTrader Open API Async с правильной OAuth авторизацией.

## 📋 Список примеров

### 1. `oauth_auth_example.py` - Полный пример OAuth авторизации

**Рекомендуется для продакшн использования**

Полный пример OAuth авторизации с автоматическим запуском локального HTTP сервера для обработки редиректа. Включает:

- Автоматический запуск локального сервера на порту 8080
- Открытие браузера для авторизации
- Автоматическое получение кода авторизации
- Обмен кода на access token
- Полный цикл работы с API

**Использование:**
```bash
python examples/oauth_auth_example.py
```

### 2. `simple_oauth_example.py` - Упрощенный OAuth пример

**Рекомендуется для обучения и быстрых тестов**

Упрощенный пример OAuth авторизации с ручным вводом кода авторизации. Включает:

- Генерацию URL для авторизации
- Ручной ввод кода авторизации
- Получение access token
- Базовые операции с API

**Использование:**
```bash
python examples/simple_oauth_example.py
```

### 3. `basic_usage.py` - Базовый пример (устаревший)

⚠️ **Устаревший пример** - не учитывает OAuth процесс авторизации. Оставлен для совместимости.

## 🔧 Настройка OAuth приложения

Перед использованием примеров необходимо настроить OAuth приложение в cTrader:

### Шаг 1: Создание приложения

1. Зайдите на [cTrader ID Portal](https://id.ctrader.com/)
2. Войдите в ваш cTrader ID аккаунт
3. Перейдите в раздел **"Applications"**
4. Нажмите **"Create New Application"**

### Шаг 2: Настройка приложения

1. **Application Name**: Введите название вашего приложения
2. **Application Type**: Выберите `Desktop Application` или `Web Application`
3. **Redirect URIs**: Добавьте URI для редиректа:
   - Для локальной разработки: `http://localhost:8080/auth/callback`
   - Для продакшн: ваш реальный URL

### Шаг 3: Получение учетных данных

После создания приложения:

1. Скопируйте **Client ID**
2. Скопируйте **Client Secret**
3. Замените значения в примерах кода

## 🔐 OAuth процесс авторизации

Согласно [документации cTrader Open API](https://help.ctrader.com/open-api/account-authentication/), процесс авторизации включает следующие шаги:

### 1. Получение кода авторизации

Пользователь перенаправляется на URL авторизации:
```
https://openapi.ctrader.com/apps/auth?client_id={CLIENT_ID}&redirect_uri={REDIRECT_URI}&response_type=code&scope={SCOPE}
```

Параметры:
- `client_id` - ID вашего приложения
- `redirect_uri` - URI для редиректа (должен быть зарегистрирован)
- `response_type` - всегда `code`
- `scope` - область доступа:
  - `accounts` - только чтение данных аккаунта
  - `trading` - полный доступ для торговли

### 2. Обмен кода на токен

После авторизации пользователь перенаправляется на `redirect_uri` с кодом:
```
http://localhost:8080/auth/callback?code=AUTHORIZATION_CODE
```

Этот код обменивается на access token через POST запрос к:
```
https://openapi.ctrader.com/apps/token
```

### 3. Использование access token

Access token используется для:
1. Получения списка аккаунтов: `ProtoOAGetAccountListByAccessTokenReq`
2. Авторизации торгового аккаунта: `ProtoOAAccountAuthReq`

## 📚 Структура примеров

### OAuth авторизация
```python
# 1. Создание URL авторизации
async with AsyncAuth(client_id, client_secret, redirect_uri) as auth:
    auth_url = auth.get_auth_uri(scope="trading")
    
    # 2. Пользователь авторизуется и получается код
    auth_code = "полученный_код"
    
    # 3. Обмен кода на токен
    token_data = await auth.get_token(auth_code)
    access_token = token_data['access_token']
```

### Подключение к API
```python
# 1. Подключение к серверу
async with AsyncClient(host, port) as client:
    # 2. Аутентификация приложения
    await client.send_application_auth_req(client_id, client_secret)
    
    # 3. Получение аккаунтов
    response = await client.send_get_account_list_by_access_token_req(access_token)
    accounts = list(response.ctidTraderAccount)
    
    # 4. Авторизация торгового аккаунта
    account_id = accounts[0].ctidTraderAccountId
    await client.send_account_auth_req(account_id, access_token)
```

## ⚠️ Важные замечания

### Безопасность

1. **Никогда не храните** `client_secret` в открытом виде в коде для продакшн
2. **Используйте переменные окружения** для конфиденциальных данных
3. **Access token** имеет ограниченное время жизни (~30 дней)
4. **Refresh token** можно использовать для обновления access token

### Redirect URI

1. **Обязательно зарегистрируйте** redirect URI в настройках приложения
2. **Для локальной разработки** используйте `http://localhost:8080/auth/callback`
3. **Для продакшн** используйте HTTPS URL

### Области доступа (Scope)

- `accounts` - доступ только для чтения:
  - Информация об аккаунте
  - Статистика
  - Исторические данные
  
- `trading` - полный доступ:
  - Все возможности `accounts`
  - Размещение/отмена ордеров
  - Управление позициями

## 🔄 Обновление токенов

```python
# Обновление access token с помощью refresh token
async with AsyncAuth(client_id, client_secret, redirect_uri) as auth:
    new_token_data = await auth.refresh_token(refresh_token)
    new_access_token = new_token_data['access_token']
```

## 🆘 Решение проблем

### Ошибка "Invalid redirect URI"
- Убедитесь, что redirect URI точно совпадает с зарегистрированным
- Проверьте протокол (http/https) и порт

### Ошибка "Invalid authorization code"
- Код авторизации имеет срок жизни 1 минута
- Убедитесь, что код не был использован ранее

### Ошибка "Invalid client credentials"
- Проверьте правильность Client ID и Client Secret
- Убедитесь, что приложение активно

## 📞 Поддержка

- [Документация cTrader Open API](https://help.ctrader.com/open-api/)
- [GitHub Issues](https://github.com/paxelcool/ctrader-open-api-async/issues)
- [cTrader ID Portal](https://id.ctrader.com/)
