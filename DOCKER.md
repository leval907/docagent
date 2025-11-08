# 🐳 Docker Guide - DocAgent Parser

Минималистичная Docker конфигурация **только для парсера** документации.

## 📦 Что внутри

- **Python 3.11** окружение
- **markdown-crawler** (автоматически клонируется)
- Все зависимости из `requirements.txt`
- Скрипты парсера (crawler, postprocessor, indexer)

## 🚀 Быстрый старт

### 1. Собрать образ

```bash
docker-compose build docagent
```

### 2. Использование

```bash
# Список доступных источников
docker-compose run --rm docagent scripts/wrapper_crawler.py --list

# Crawl одного приложения
docker-compose run --rm docagent scripts/wrapper_crawler.py --app dbgpt

# Добавить метаданные
docker-compose run --rm docagent scripts/postprocess.py --app dbgpt

# Создать индекс
docker-compose run --rm docagent scripts/build_index.py --app dbgpt
```

### 3. Полный pipeline

```bash
# Весь pipeline для dbgpt
docker-compose run --rm docagent scripts/wrapper_crawler.py --app dbgpt && \
docker-compose run --rm docagent scripts/postprocess.py --app dbgpt && \
docker-compose run --rm docagent scripts/build_index.py --app dbgpt
```

## 📁 Структура volumes

```yaml
volumes:
  - ./knowledge_base:/app/knowledge_base  # Результаты парсинга
  - ./logs:/app/logs                      # Логи
  - ./config:/app/config:ro               # Конфигурация (read-only)
```

Все результаты сохраняются в локальную директорию `knowledge_base/`.

## 🔧 Конфигурация

Отредактируйте `config/sources.yaml` перед запуском:

```yaml
apps:
  dbgpt:
    url: "https://docs.dbgpt.cn/docs/awel/cookbook/"
    depth: 2
    enabled: true
```

## 💡 Полезные команды

```bash
# Проверить что образ собрался
docker images | grep docagent

# Логи в реальном времени
tail -f logs/*.log

# Очистить всё
docker-compose down --rmi all
```

## 🎯 Интеграция с существующими сервисами

Парсер сохраняет результаты в `knowledge_base/`, которую можно:

- Монтировать в **n8n** для автоматизации
- Загружать в **Flowise** для RAG
- Индексировать в **Qdrant** через векторизацию
- Импортировать в **OpenSPG** для Knowledge Graph

## ⚙️ Переменные окружения (опционально)

Можно добавить в `docker-compose.yml`:

```yaml
environment:
  - CRAWL_DELAY=0.5       # Задержка между запросами
  - MAX_DEPTH=3           # Глубина обхода
  - OUTPUT_DIR=/app/kb    # Кастомная директория
```

## 📊 Пример вывода

```bash
$ docker-compose run --rm docagent scripts/wrapper_crawler.py --app dbgpt

23:45:12 | INFO     | DocAgent Crawler initialized
23:45:12 | INFO     | Config: /app/config/sources.yaml
23:45:12 | INFO     | 🚀 Starting crawl for: DB-GPT
23:45:12 | INFO     |    URL: https://docs.dbgpt.cn/docs/awel/cookbook/
23:45:12 | INFO     |    Output: /app/knowledge_base/dbgpt
...
23:45:45 | SUCCESS  | ✅ Crawl completed in 33.2s
23:45:45 | SUCCESS  |    Files: 15 markdown files
```

## 🔗 Что дальше?

После настройки парсера:
1. Настроить регулярный запуск через **cron** или **n8n**
2. Интегрировать с вашими существующими сервисами
3. Настроить уведомления об обновлениях

---

**Примечание:** Этот Docker образ содержит **только парсер**. Другие сервисы (n8n, Flowise, etc.) запускаются отдельно на вашем сервере.
