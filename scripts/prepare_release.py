#!/usr/bin/env python3
"""Скрипт для подготовки релиза cTrader Open API Async."""

import os
import sys
import subprocess
import shutil
from pathlib import Path


def run_command(command: str, check: bool = True) -> subprocess.CompletedProcess:
    """Выполняет команду в shell."""
    print(f"Выполняется: {command}")
    result = subprocess.run(command, shell=True, capture_output=True, text=True)
    
    if check and result.returncode != 0:
        print(f"Ошибка выполнения команды: {command}")
        print(f"Код возврата: {result.returncode}")
        print(f"Stdout: {result.stdout}")
        print(f"Stderr: {result.stderr}")
        sys.exit(1)
    
    return result


def clean_project():
    """Очищает проект от временных файлов."""
    print("🧹 Очистка проекта...")
    
    # Директории для удаления
    dirs_to_remove = [
        "build",
        "dist", 
        "*.egg-info",
        "__pycache__",
        ".pytest_cache",
        ".mypy_cache",
        ".coverage"
    ]
    
    for pattern in dirs_to_remove:
        run_command(f"find . -name '{pattern}' -type d -exec rm -rf {{}} + 2>/dev/null || true", check=False)
    
    # Файлы для удаления
    files_to_remove = [
        "*.pyc",
        "*.pyo", 
        "*.pyd",
        ".coverage",
        "coverage.xml"
    ]
    
    for pattern in files_to_remove:
        run_command(f"find . -name '{pattern}' -type f -delete 2>/dev/null || true", check=False)
    
    print("✅ Проект очищен")


def check_dependencies():
    """Проверяет наличие необходимых зависимостей."""
    print("🔍 Проверка зависимостей...")
    
    required_tools = ["black", "ruff", "mypy", "pytest", "build", "twine"]
    
    for tool in required_tools:
        result = run_command(f"which {tool}", check=False)
        if result.returncode != 0:
            print(f"❌ {tool} не найден. Установите: pip install {tool}")
            return False
    
    print("✅ Все зависимости найдены")
    return True


def format_code():
    """Форматирует код."""
    print("🎨 Форматирование кода...")
    
    run_command("black .")
    run_command("ruff check . --fix")
    
    print("✅ Код отформатирован")


def run_tests():
    """Запускает тесты."""
    print("🧪 Запуск тестов...")
    
    result = run_command("pytest --cov=ctrader_open_api_async --cov-report=term-missing", check=False)
    
    if result.returncode != 0:
        print("❌ Тесты не прошли")
        return False
    
    print("✅ Все тесты прошли")
    return True


def type_check():
    """Проверяет типы."""
    print("🔍 Проверка типов...")
    
    result = run_command("mypy ctrader_open_api_async", check=False)
    
    if result.returncode != 0:
        print("⚠️ Найдены проблемы с типизацией (не критично)")
        print(result.stdout)
    else:
        print("✅ Проверка типов прошла")
    
    return True


def build_package():
    """Собирает пакет."""
    print("📦 Сборка пакета...")
    
    run_command("python -m build")
    
    print("✅ Пакет собран")


def check_package():
    """Проверяет собранный пакет."""
    print("🔍 Проверка пакета...")
    
    run_command("twine check dist/*")
    
    print("✅ Пакет проверен")


def update_version():
    """Обновляет версию в файлах."""
    print("📝 Обновление версии...")
    
    # Здесь можно добавить логику автоматического обновления версии
    # Пока просто выводим текущую версию
    
    init_file = Path("ctrader_open_api_async/__init__.py")
    if init_file.exists():
        with open(init_file, 'r') as f:
            content = f.read()
            for line in content.split('\n'):
                if '__version__' in line:
                    print(f"Текущая версия: {line}")
                    break
    
    print("✅ Версия проверена")


def main():
    """Основная функция."""
    print("🚀 Подготовка релиза cTrader Open API Async")
    print("=" * 50)
    
    # Проверяем, что мы в корне проекта
    if not Path("ctrader_open_api_async").exists():
        print("❌ Запустите скрипт из корня проекта")
        sys.exit(1)
    
    # Проверяем зависимости
    if not check_dependencies():
        sys.exit(1)
    
    # Очищаем проект
    clean_project()
    
    # Обновляем версию
    update_version()
    
    # Форматируем код
    format_code()
    
    # Проверяем типы
    type_check()
    
    # Запускаем тесты
    if not run_tests():
        print("❌ Релиз не может быть подготовлен из-за неудачных тестов")
        sys.exit(1)
    
    # Собираем пакет
    build_package()
    
    # Проверяем пакет
    check_package()
    
    print("\n🎉 Релиз готов!")
    print("📦 Файлы пакета находятся в директории dist/")
    print("🚀 Для публикации на PyPI выполните: twine upload dist/*")
    print("\n📋 Следующие шаги:")
    print("1. Проверьте файлы в dist/")
    print("2. Создайте git tag с версией")
    print("3. Опубликуйте на PyPI")
    print("4. Создайте GitHub Release")


if __name__ == "__main__":
    main() 