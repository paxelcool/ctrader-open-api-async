# Инструкции по созданию форка cTrader Open API Async

Этот документ содержит пошаговые инструкции по созданию форка от оригинального проекта [OpenApiPy](https://github.com/spotware/OpenApiPy) и публикации вашей async/await версии.

## 🚀 Шаги для создания форка

### 1. Подготовка GitHub репозитория

1. **Создайте новый репозиторий на GitHub**:
   - Название: `ctrader-open-api-async`
   - Описание: `Async/await версия cTrader Open API библиотеки`
   - Сделайте его публичным
   - Не инициализируйте с README, .gitignore или лицензией

2. **Клонируйте ваш новый репозиторий**:
   ```bash
   git clone https://github.com/yourusername/ctrader-open-api-async.git
   cd ctrader-open-api-async
   ```

3. **Скопируйте файлы из текущего проекта**:
   ```bash
   # Скопируйте все файлы кроме .git, .venv и временных
   cp -r /path/to/current/project/* .
   cp -r /path/to/current/project/.github .
   cp /path/to/current/project/.gitignore .
   ```

### 2. Настройка проекта

1. **Обновите URL в файлах**:
   
   В `setup.py`, `pyproject.toml`, `README.md` замените:
   ```
   yourusername -> ваш_github_username
   ```

2. **Обновите информацию об авторе**:
   
   В `setup.py`, `pyproject.toml`, `AUTHORS.md` замените:
   ```
   AsyncIO Port Team -> Ваше имя
   async@ctrader.com -> ваш_email@example.com
   ```

### 3. Инициализация Git

```bash
# Инициализируйте git (если еще не сделано)
git init

# Добавьте оригинальный репозиторий как upstream
git remote add upstream https://github.com/spotware/OpenApiPy.git

# Добавьте ваш репозиторий как origin
git remote add origin https://github.com/yourusername/ctrader-open-api-async.git

# Создайте первый коммит
git add .
git commit -m "feat: initial async/await port of cTrader Open API"

# Отправьте в ваш репозиторий
git push -u origin main
```

### 4. Настройка виртуального окружения

```bash
# Создайте виртуальное окружение
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# или
.venv\Scripts\activate  # Windows

# Установите зависимости для разработки
pip install -e .[dev]
```

### 5. Проверка проекта

```bash
# Запустите скрипт подготовки релиза
python scripts/prepare_release.py

# Или выполните проверки вручную:
black .
ruff check .
mypy ctrader_open_api_async
pytest
```

### 6. Создание первого релиза

1. **Обновите версию** в `ctrader_open_api_async/__init__.py` и `pyproject.toml`

2. **Создайте git tag**:
   ```bash
   git tag -a v2.0.0 -m "Release v2.0.0: Async/await port"
   git push origin v2.0.0
   ```

3. **Создайте GitHub Release**:
   - Перейдите на GitHub в раздел Releases
   - Нажмите "Create a new release"
   - Выберите тег v2.0.0
   - Заполните описание релиза

### 7. Публикация на PyPI

1. **Зарегистрируйтесь на PyPI** (если еще не сделано):
   - Перейдите на [pypi.org](https://pypi.org)
   - Создайте аккаунт
   - Настройте 2FA

2. **Создайте API токен**:
   - Перейдите в Account settings → API tokens
   - Создайте токен для проекта

3. **Соберите и опубликуйте пакет**:
   ```bash
   # Соберите пакет
   python -m build
   
   # Проверьте пакет
   twine check dist/*
   
   # Опубликуйте на PyPI
   twine upload dist/*
   ```

### 8. Настройка GitHub Actions

1. **Добавьте секреты в GitHub**:
   - Перейдите в Settings → Secrets and variables → Actions
   - Добавьте `PYPI_API_TOKEN` с вашим PyPI токеном

2. **GitHub Actions автоматически**:
   - Запустят тесты при каждом push/PR
   - Опубликуют на PyPI при создании release

## 📋 Чек-лист готовности

- [ ] Репозиторий создан на GitHub
- [ ] Все файлы скопированы и настроены
- [ ] URL и информация об авторе обновлены
- [ ] Git настроен с upstream и origin
- [ ] Виртуальное окружение создано
- [ ] Зависимости установлены
- [ ] Тесты проходят
- [ ] Код отформатирован
- [ ] Первый коммит создан
- [ ] GitHub Actions настроены
- [ ] PyPI аккаунт готов

## 🔄 Синхронизация с оригиналом

Для получения обновлений из оригинального репозитория:

```bash
# Получите изменения из upstream
git fetch upstream

# Создайте ветку для обновлений
git checkout -b update-from-upstream

# Слейте изменения (может потребоваться разрешение конфликтов)
git merge upstream/main

# Адаптируйте изменения под async/await
# ... внесите необходимые изменения ...

# Создайте PR в ваш main
git push origin update-from-upstream
```

## 📞 Поддержка

Если возникли вопросы:

1. Проверьте [документацию GitHub](https://docs.github.com/en/get-started/quickstart/fork-a-repo)
2. Изучите [руководство по PyPI](https://packaging.python.org/en/latest/tutorials/packaging-projects/)
3. Обратитесь к [документации cTrader API](https://help.ctrader.com/open-api/)

## 🎉 Поздравления!

После выполнения всех шагов у вас будет:

- ✅ Полноценный форк с async/await реализацией
- ✅ Автоматические тесты и CI/CD
- ✅ Пакет, доступный через pip install
- ✅ Профессиональная документация
- ✅ Готовность к развитию и поддержке

Удачи с вашим проектом! 🚀 