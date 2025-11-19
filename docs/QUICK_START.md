# 🚀 DocAgent - Быстрый старт

## 📦 Шаг 1: Автоматическая установка

### Вариант 1: Windows (PowerShell)

```powershell
# Запустить setup скрипт
.\setup.ps1
```

### Вариант 2: Linux/Mac (Bash)

```bash
# Запустить setup скрипт
bash setup.sh
```

Скрипт автоматически:
- ✅ Создаст виртуальное окружение `venv`
- ✅ Установит все зависимости
- ✅ Клонирует и настроит markdown-crawler
- ✅ Создаст необходимые директории

## 📦 Шаг 1 (альтернатива): Ручная установка

### 1.1 Создать виртуальное окружение

```bash
# Создать venv
python -m venv venv

# Активировать (Windows PowerShell)
.\venv\Scripts\Activate.ps1

# Активировать (Linux/Mac)
source venv/bin/activate
```

### 1.2 Установить зависимости

```bash
# Обновить pip
pip install --upgrade pip

# Установить зависимости DocAgent
pip install -r requirements.txt
```

### 1.3 Установить markdown-crawler

```bash
# Клонировать
mkdir tools
cd tools
git clone https://github.com/paulpierre/markdown-crawler.git

# Установить как пакет
cd markdown-crawler
pip install -e .
cd ../..
```

## 🔧 Шаг 2: Конфигурация

Отредактируйте `config/sources.yaml` при необходимости:

```yaml
apps:
  dbgpt:
    name: "DB-GPT"
    url: "https://docs.dbgpt.cn/docs/awel/cookbook/"
    depth: 2
    enabled: true
```

## 🧪 Шаг 3: Тестирование

### Вариант 1: Интерактивный тест

```bash
python tests/test_crawler.py
```

Выберите опцию `4` для полного теста пайплайна.

### Вариант 2: Ручной запуск

```bash
# 1. Список доступных источников
python scripts/wrapper_crawler.py --list

# 2. Dry-run (тест без реального скачивания)
python scripts/wrapper_crawler.py --app dbgpt --dry-run

# 3. Реальный crawling
python scripts/wrapper_crawler.py --app dbgpt

# 4. Добавление метаданных
python scripts/postprocess.py --app dbgpt

# 5. Создание индекса
python scripts/build_index.py --app dbgpt

# 6. Поиск по индексу
python scripts/build_index.py --search "RAG" --app dbgpt
```

## 📁 Структура результатов

После выполнения вы получите:

```
knowledge_base/
└── dbgpt/
    ├── index.json                    # Индекс приложения
    ├── first_rag_with_awel.md       # Markdown с YAML метаданными
    ├── multi_round_chat_withllm.md
    └── ...
```

Пример markdown файла с метаданными:

```markdown
---
title: "First RAG with AWEL"
source: "https://docs.dbgpt.cn/docs/awel/cookbook/first_rag_with_awel"
app: "dbgpt"
category: "ai-frameworks"
tags:
  - "awel"
  - "rag"
date_crawled: "2024-11-08T10:30:00"
word_count: 1250
has_code: true
---

# First RAG with AWEL
...
```

## 🔍 Проверка результатов

### Проверить индекс

```bash
# Посмотреть индекс приложения
cat knowledge_base/dbgpt/index.json

# Построить глобальный индекс
python scripts/build_index.py --all

# Посмотреть глобальный индекс
cat global_index.json
```

### Проверить метаданные

```bash
# Посмотреть первые 30 строк любого файла
head -n 30 knowledge_base/dbgpt/*.md
```

## 🎯 Следующие шаги

После успешного тестирования:

1. ✅ Базовый парсинг работает
2. ⏳ Настроить автоматизацию через n8n
3. ⏳ Интегрировать с Flowise/OpenSPG
4. ⏳ Настроить векторное хранилище (Qdrant)

## 🐛 Решение проблем

### Ошибка: markdown-crawler not found

```bash
# Убедитесь что клонировали в правильную директорию
ls tools/markdown-crawler/markdown_crawler.py

# Если нет, клонируйте заново
mkdir -p tools
cd tools
git clone https://github.com/paulpierre/markdown-crawler.git
```

### Ошибка: ModuleNotFoundError

```bash
# Установите все зависимости
pip install -r requirements.txt

# Для markdown-crawler
cd tools/markdown-crawler
pip install -r requirements.txt
```

### Ошибка: Permission denied (Windows)

```powershell
# Запустите PowerShell как администратор или используйте:
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

## 📊 Пример вывода успешного теста

```
🚀 FULL PIPELINE TEST
============================================================
✅ Step: Crawler - SUCCESS
✅ Step: Postprocessor - SUCCESS
✅ Step: Indexer - SUCCESS

📊 PIPELINE TEST RESULTS
============================================================
✅ PASS - Crawler
✅ PASS - Postprocessor
✅ PASS - Indexer

🎉 All tests passed!
```

## 💡 Дополнительные команды

```bash
# Обработать все приложения сразу
python scripts/wrapper_crawler.py --all
python scripts/postprocess.py --all
python scripts/build_index.py --all

# Перезаписать существующие метаданные
python scripts/postprocess.py --app dbgpt --force

# Подробный вывод
python scripts/wrapper_crawler.py --app dbgpt --verbose
```

## 📝 Готово!

Теперь у вас есть рабочий парсер документации с:
- ✅ Автоматическим сбором markdown
- ✅ YAML метаданными
- ✅ JSON индексами
- ✅ Возможностью поиска

Можно переходить к интеграции с AI системами! 🎉
