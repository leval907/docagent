# 🤖 DocAgent - AI-Powered Documentation Pipeline

Автоматизированный сбор, обработка и векторный поиск по технической документации.

## 🚀 Два режима работы

### 🧪 **Lite Mode** - Для экспериментов (рекомендуется для старта)

**Легковесная версия на SQLite** без Docker:
- ✅ Chunking текста с настраиваемым размером
- ✅ Локальные embeddings через sentence-transformers
- ✅ Векторный поиск через cosine similarity
- ✅ Один файл базы данных (SQLite)
- ✅ Быстрый старт за 3 минуты

👉 **[QUICKSTART_LITE.md](./QUICKSTART_LITE.md)** - Начните отсюда!

### 🏢 **Production Mode** - Для реальных проектов

**Полный стек с Docker:**
- PostgreSQL 18 + pgvector для метаданных
- ChromaDB для векторного поиска
- Prefect для workflow orchestration
- FastAPI для REST API
- DuckDB для аналитики

👉 **[COMPLETE_STACK.md](./COMPLETE_STACK.md)** - Production deployment

## 🎯 Основные возможности

- �️ **Smart Crawling**: Crawl4AI с поддержкой JavaScript (React, Vue, SPA)
- 📄 **Chunking**: Умная разбивка документов с overlap
- 🧠 **Embeddings**: Локальные (sentence-transformers) или API (OpenAI)
- 🔍 **Vector Search**: Семантический поиск по документации
- ☁️ **S3 Storage**: Совместимость с Beget, AWS, MinIO
- �️ **Flexible DB**: SQLite для экспериментов, PostgreSQL для production
- 🔄 **Automation**: Prefect workflows для автоматизации

## ⚡ Quick Start (3 минуты)

```bash
# 1. Установка
pip install sentence-transformers crawl4ai

# 2. Загрузка документов
cd D:\docs\DocAgent
Get-ChildItem "knowledge_base\openspg\*.md" | ForEach-Object {
    python scripts\pipeline_lite.py load $_.FullName --app openspg
}

# 3. Поиск
python scripts\pipeline_lite.py search "knowledge graph" --app openspg

# 4. Статистика
python scripts\pipeline_lite.py stats
```

**Результат за 3 минуты:**
```
🔍 Найдено результатов: 5

1. [Document Title] (0.847) ⭐
   Текст: OpenSPG is a knowledge graph engine...

2. [Another Doc] (0.782)
   ...
```

## 🧪 Что нового

**v3.0 - Lite Pipeline** (текущая версия):
- ✅ SQLite для быстрых экспериментов
- ✅ Локальные embeddings без API ключей
- ✅ Chunking + векторный поиск работает
- ✅ Протестировано на OpenSPG документации

**v2.0 - Production Stack**:
- ✅ PostgreSQL 18 + pgvector
- ✅ ChromaDB + Prefect + FastAPI
- ✅ Docker Compose с 6 сервисами
- ✅ Полная документация и деплой скрипты

## 🚀 Быстрый старт

### Установка

**Автоматическая (рекомендуется)**:
```powershell
# Windows PowerShell
.\setup.ps1

# Linux/Mac
chmod +x setup.sh && ./setup.sh
```

**Ручная установка**:
```bash
# Создать виртуальное окружение
python -m venv .venv
.venv\Scripts\Activate.ps1  # Windows

# Установить зависимости
pip install -r requirements.txt

# Установить браузеры для Playwright
playwright install
```
cd ../..

# Установить зависимости DocAgent
pip install -r requirements.txt
```

### Базовое использование

```bash
# Сбор документации (с JavaScript support)
python scripts/crawler_crawl4ai.py --app nocodb

# Обработка и добавление метаданных (если нужно)
python scripts/postprocess.py --app nocodb

# Создание индекса
python scripts/build_index.py --app nocodb
```


## 📁 Структура проекта

```
DocAgent/
├── scripts/
│   ├── pipeline_lite.py       # 🧪 Lite: SQLite + embeddings + search ⭐
│   ├── crawl_and_clean.py     # 🏢 Production: Full pipeline с S3
│   ├── crawler_crawl4ai.py    # Базовый crawler с Crawl4AI
│   └── test_*.py              # Тесты
├── api/
│   └── main.py                # 🏢 FastAPI REST API
├── workflows/
│   └── prefect_flows.py       # 🏢 Prefect orchestration
├── config/
│   └── sources.yaml           # Конфигурация источников
├── knowledge_base/
│   └── {app}/                 # Markdown файлы по приложениям
├── QUICKSTART_LITE.md         # 🧪 Quick start для экспериментов
├── LITE_PIPELINE.md           # 🧪 Детальная документация Lite
├── COMPLETE_STACK.md          # 🏢 Production stack guide
├── DOCKER_SETUP.md            # 🏢 Docker конфигурация
└── requirements.txt           # Python dependencies
```

## 🔧 Использование

### Lite Mode (для экспериментов)

```bash
# Загрузка документа
python scripts/pipeline_lite.py load document.md --app myapp

# Поиск
python scripts/pipeline_lite.py search "your query" --limit 10

# Статистика
python scripts/pipeline_lite.py stats
```

### Production Mode (полный стек)

```bash
# Docker Compose
docker network create ducem-net
docker compose up -d

# Краулинг + обработка
python scripts/crawl_and_clean.py --app openspg \
  --s3-bucket your-bucket \
  --s3-endpoint https://s3.endpoint.com

# API доступ
curl http://localhost:8080/search -d '{"query": "text"}'
```

## 📊 Примеры результатов

### Lite Pipeline (SQLite)

```
📊 Статистика
Документов: 5
Chunks: 10
Приложения: openspg (5 docs, 3091 words)

🔍 Поиск: "knowledge graph"
1. [Schema Guide] (0.847) - высокая релевантность
2. [Tutorial] (0.782) - хорошее совпадение
3. [Concepts] (0.691) - релевантно
```

### Production Stack

```json
GET /stats/analytics
{
  "total_documents": 127,
  "total_chunks": 1534,
  "apps": [
    {"app_id": "openspg", "documents": 24, "words": 16408},
    {"app_id": "nocodb", "documents": 50, "words": 26988},
    {"app_id": "dbgpt", "documents": 53, "words": 34512}
  ]
}
```


## � Документация

### 🧪 Для экспериментов (начните отсюда)
- **[QUICKSTART_LITE.md](./QUICKSTART_LITE.md)** - Быстрый старт за 3 минуты
- **[LITE_PIPELINE.md](./LITE_PIPELINE.md)** - Полное руководство по Lite режиму
- **[scripts/pipeline_lite.py](./scripts/pipeline_lite.py)** - Исходный код

### 🏢 Для production
- **[COMPLETE_STACK.md](./COMPLETE_STACK.md)** - Полный production stack
- **[DOCKER_SETUP.md](./DOCKER_SETUP.md)** - Docker конфигурация
- **[SERVER_DEPLOYMENT.md](./SERVER_DEPLOYMENT.md)** - Деплой на сервер

### 📖 Дополнительно
- **[CRAWL4AI_GUIDE.md](./CRAWL4AI_GUIDE.md)** - Crawl4AI integration
- **[PIPELINE_GUIDE.md](./PIPELINE_GUIDE.md)** - Детали pipeline
- **[config/sources.yaml](./config/sources.yaml)** - Конфигурация источников

## 🛠️ Roadmap

### ✅ Completed
- [x] Crawl4AI integration с JavaScript support
- [x] SQLite lite pipeline для экспериментов
- [x] Chunking + embeddings + vector search
- [x] PostgreSQL 18 + pgvector
- [x] ChromaDB integration
- [x] Prefect workflows
- [x] FastAPI REST API
- [x] S3 storage (Beget, AWS, MinIO)
- [x] Docker Compose stack

### 🔄 In Progress
- [ ] FAISS индексы для быстрого поиска
- [ ] Гибридный поиск (BM25 + Vector)
- [ ] Reranking с cross-encoder

### 📋 Planned
- [ ] n8n workflow integration
- [ ] Flowise connector
- [ ] OpenSPG knowledge graph integration
- [ ] Grafana dashboards
- [ ] API authentication (JWT)

## 🤝 Contributing

Pull requests приветствуются! См. [CONTRIBUTING.md](./CONTRIBUTING.md)

1. Fork проекта
2. Создайте feature branch (`git checkout -b feature/amazing`)
3. Commit изменений (`git commit -m 'Add amazing feature'`)
4. Push в branch (`git push origin feature/amazing`)
5. Откройте Pull Request

## 📝 Лицензия

MIT
