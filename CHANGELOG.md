# Changelog

Все значимые изменения в этом проекте будут документированы в этом файле.

Формат основан на [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
и этот проект придерживается [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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