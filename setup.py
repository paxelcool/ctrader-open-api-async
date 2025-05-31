#!/usr/bin/env python3
"""Setup script для cTrader Open API Async."""

import os

from setuptools import find_packages, setup


# Читаем README файл
def read_readme():
    """Читает содержимое README.md файла."""
    readme_path = os.path.join(os.path.dirname(__file__), 'README.md')
    if os.path.exists(readme_path):
        with open(readme_path, encoding='utf-8') as f:
            return f.read()
    return ""

# Читаем requirements
def read_requirements():
    """Читает зависимости из requirements.txt."""
    requirements_path = os.path.join(os.path.dirname(__file__), 'requirements.txt')
    requirements = []
    if os.path.exists(requirements_path):
        with open(requirements_path, encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    requirements.append(line)
    return requirements

setup(
    name="ctrader-open-api-async",
    version="2.0.0",
    author="Pavel Sadovenko",
    author_email="paxelcool@gmail.com",
    description="Async/await версия cTrader Open API библиотеки",
    long_description=read_readme(),
    long_description_content_type="text/markdown",
    url="https://github.com/paxelcool/ctrader-open-api-async",
    project_urls={
        "Bug Tracker": "https://github.com/paxelcool/ctrader-open-api-async/issues",
        "Documentation": "https://github.com/paxelcool/ctrader-open-api-async/blob/main/README.md",
        "Source Code": "https://github.com/paxelcool/ctrader-open-api-async",
        "Original Project": "https://github.com/spotware/OpenApiPy"
    },
    packages=find_packages(),
    include_package_data=True,
    package_data={
        'ctrader_open_api_async': ['messages/*.py'],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: Office/Business :: Financial :: Investment",
        "Framework :: AsyncIO",
    ],
    python_requires=">=3.8",
    install_requires=read_requirements(),
    extras_require={
        "dev": [
            "black",
            "mypy",
            "pytest",
            "pytest-asyncio",
            "pytest-cov",
        ],
        "docs": [
            "mkdocs",
            "mkdocs-material",
        ],
    },
    keywords="ctrader, trading, api, async, asyncio, forex, cfd",
    zip_safe=False,
)
