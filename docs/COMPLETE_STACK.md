# 🚀 DocAgent - Complete Production Pipeline

**Full-stack documentation processing pipeline** с PostgreSQL 18, ChromaDB, Prefect, FastAPI и DuckDB.

## 📦 Технологический стек

- **🕷️ Crawler**: Crawl4AI + Playwright (JavaScript support)
- **🗄️ Metadata DB**: PostgreSQL 18 + pgvector
- **🧠 Vector DB**: ChromaDB для семантического поиска
- **⚡ Orchestration**: Prefect 2.0 для workflow management
- **🌐 API**: FastAPI для REST endpoints
- **📊 Analytics**: DuckDB для быстрой аналитики
- **☁️ Storage**: S3-compatible (Beget, AWS, MinIO)

## 🏗️ Архитектура

```
┌─────────────┐    ┌──────────────┐    ┌─────────┐    ┌────────────┐
│  Crawl4AI   │ -> │  PostgreSQL  │ -> │ ChromaDB│ -> │  FastAPI   │
│  (Scraper)  │    │  (Metadata)  │    │ (Vector)│    │    (API)   │
└─────────────┘    └──────────────┘    └─────────┘    └────────────┘
       │                   │                  │              │
       v                   v                  v              v
┌─────────────┐    ┌──────────────┐    ┌─────────┐    ┌────────────┐
│     S3      │    │   Prefect    │    │ DuckDB  │    │   Client   │
│  (Storage)  │    │(Orchestrator)│    │(Analytics)│   │   Apps     │
└─────────────┘    └──────────────┘    └─────────┘    └────────────┘
```

## 🎯 Возможности

✅ **Intelligent Crawling** - Async краулинг с поддержкой JavaScript  
✅ **Vector Search** - Семантический поиск через ChromaDB  
✅ **Workflow Automation** - Prefect flows для автоматизации  
✅ **REST API** - FastAPI endpoints для интеграции  
✅ **Analytics** - DuckDB для быстрых SQL-запросов  
✅ **S3 Storage** - Совместимость с Beget, AWS, MinIO  
✅ **PostgreSQL 18** - Метаданные с pgvector поддержкой  

## 🚀 Быстрый старт

### 1. Клонирование и настройка

```bash
git clone https://github.com/leval907/docagent.git
cd docagent

cp .env.example .env
nano .env  # настроить credentials
```

### 2. Запуск всего стека

```bash
# Создать сеть (если не существует)
docker network create ducem-net

# Запустить все сервисы
docker compose up -d

# Проверить статус
docker compose ps
```

### 3. Доступ к сервисам

- **FastAPI Docs**: http://localhost:8080/docs
- **Prefect UI**: http://localhost:4200
- **ChromaDB**: http://localhost:8000
- **PostgreSQL**: localhost:5436

### 4. Запуск краулера

```bash
# Через Docker Compose
docker compose --profile crawler run --rm -e APP=openspg crawler

# Или напрямую
python scripts/crawl_and_clean.py --app openspg \
  --s3-bucket your-bucket \
  --s3-endpoint https://s3.ru1.storage.beget.cloud
```

### 5. Использование API

```bash
# Проверка здоровья
curl http://localhost:8080/health

# Список документов
curl http://localhost:8080/documents?app_id=openspg

# Векторный поиск
curl -X POST http://localhost:8080/search \
  -H "Content-Type: application/json" \
  -d '{"query": "knowledge graph", "limit": 5}'

# Статистика
curl http://localhost:8080/stats/analytics
```

## 📊 Структура сервисов

### PostgreSQL 18 + pgvector
- **Порт**: 5436
- **База**: `docagent`
- **Таблицы**: `documents`, `crawl_stats`, `document_embeddings`
- **Расширения**: `vector` для векторного поиска

### ChromaDB
- **Порт**: 8000
- **Collection**: `documents`
- **Embeddings**: Автоматическая генерация
- **Persistence**: `/opt/docagent/chromadata`

### Prefect
- **Порт**: 4200
- **Flows**: `process-documentation`, `scheduled-crawl`
- **Backend**: PostgreSQL для метаданных

### FastAPI
- **Порт**: 8080
- **Endpoints**: `/documents`, `/search`, `/stats`, `/apps`
- **Docs**: Swagger UI на `/docs`

### DuckDB
- **Path**: `/opt/docagent/data/analytics.duckdb`
- **Usage**: Быстрая аналитика поверх PostgreSQL
- **Attach**: Прямое подключение к Postgres

## 🔧 Конфигурация

### .env файл

```bash
# S3 (Beget)
AWS_ACCESS_KEY_ID=JQDHVXZY7XFWUHF8LV0S
AWS_SECRET_ACCESS_KEY=pjVG1Zt5G6y8N8eYAmPnKcnnPpfxB3KVCcFrEyfk
S3_ENDPOINT=https://s3.ru1.storage.beget.cloud
S3_BUCKET=db6a1f644d97-la-ducem1

# PostgreSQL
POSTGRES_USER=docagent
POSTGRES_PASSWORD=secure_pass_2025
POSTGRES_DB=docagent
POSTGRES_PORT=5436

# ChromaDB
CHROMA_PORT=8000
CHROMA_URL=http://chromadb:8000

# Prefect
PREFECT_PORT=4200
PREFECT_API_URL=http://prefect-server:4200/api

# FastAPI
API_PORT=8080
CORS_ORIGINS=*

# Network
NETWORK_NAME=ducem-net
NETWORK_EXTERNAL=true
```

## 🔄 Prefect Workflows

### Запуск flow вручную

```bash
# Зайти в контейнер
docker compose run --rm crawler bash

# Запустить flow
python workflows/prefect_flows.py
```

### Деплой flow в Prefect

```python
from workflows.prefect_flows import process_documentation_flow

# Создание deployment
process_documentation_flow.deploy(
    name="openspg-daily",
    work_pool_name="default-agent-pool",
    cron="0 2 * * *",  # Каждый день в 2:00
    parameters={"app_id": "openspg"}
)
```

## 📡 API Endpoints

### Documents

```bash
GET  /documents              # Список документов
GET  /documents/{id}         # Документ по ID
GET  /apps                   # Список приложений
```

### Search

```bash
POST /search                 # Векторный поиск
{
  "query": "search text",
  "app_id": "openspg",      # опционально
  "limit": 10
}
```

### Statistics

```bash
GET  /stats/crawls           # Статистика краулинга
GET  /stats/analytics        # DuckDB аналитика
```

### Health

```bash
GET  /health                 # Статус сервисов
GET  /                       # API info
```

## 🔍 Векторный поиск

### Через API

```python
import requests

response = requests.post(
    "http://localhost:8080/search",
    json={
        "query": "How to build knowledge graph?",
        "app_id": "openspg",
        "limit": 5
    }
)

results = response.json()
for result in results:
    print(f"{result['title']}: {result['similarity']:.3f}")
    print(f"  {result['chunk_text'][:200]}...")
```

### Напрямую через ChromaDB

```python
import chromadb

client = chromadb.HttpClient(host="localhost", port=8000)
collection = client.get_collection("documents")

results = collection.query(
    query_texts=["knowledge graph"],
    n_results=5
)
```

## 📊 Аналитика с DuckDB

```sql
-- Подключение к PostgreSQL
ATTACH 'postgresql://docagent:secure_pass_2025@localhost:5436/docagent' 
AS pg (TYPE postgres);

-- Топ приложений по количеству документов
SELECT 
    app_id,
    COUNT(*) as docs,
    SUM(word_count) as total_words
FROM pg.documents
GROUP BY app_id
ORDER BY docs DESC;

-- Динамика краулинга
SELECT 
    DATE(completed_at) as date,
    SUM(pages_crawled) as total_pages,
    AVG(duration_seconds) as avg_duration
FROM pg.crawl_stats
GROUP BY date
ORDER BY date DESC;
```

## 🔌 Интеграция

### С Flowise

```yaml
Vector Store: ChromaDB
Host: chromadb:8000  # если в ducem-net
Collection: documents
```

### С n8n

```json
{
  "url": "http://docagent-api:8080",
  "endpoints": {
    "search": "/search",
    "documents": "/documents"
  }
}
```

### С OpenSPG

```bash
POSTGRES_URL=postgresql://docagent:secure_pass_2025@postgres18:5432/docagent
VECTOR_DB_URL=http://chromadb:8000
```

## 🛠️ Разработка

### Локальный запуск (без Docker)

```bash
# Виртуальное окружение
python3 -m venv venv
source venv/bin/activate

# Установка зависимостей
pip install -r requirements.txt
pip install -r requirements.api.txt

# Установка Playwright
playwright install chromium

# Запуск API
uvicorn api.main:app --reload --port 8080

# Запуск краулера
python scripts/crawl_and_clean.py --app openspg
```

### Тестирование

```bash
# API тесты
pytest tests/test_api.py

# Workflow тесты
pytest tests/test_workflows.py

# Интеграционные тесты
pytest tests/integration/
```

## 📦 Деплой на сервер

```bash
# На сервере
cd /opt/docagent
git pull origin main

# Пересборка контейнеров
docker compose build --no-cache

# Рестарт сервисов
docker compose down
docker compose up -d

# Проверка
docker compose ps
docker compose logs -f
```

## 🔒 Безопасность

### Firewall

```bash
sudo ufw allow 22/tcp   # SSH
sudo ufw allow 8080/tcp # API (опционально)
sudo ufw deny 5436      # PostgreSQL (внутренний)
sudo ufw deny 8000      # ChromaDB (внутренний)
sudo ufw deny 4200      # Prefect (внутренний)
```

### SSL/TLS для API

Используйте Nginx как reverse proxy:

```nginx
server {
    listen 443 ssl;
    server_name api.yourdomain.com;
    
    ssl_certificate /etc/letsencrypt/live/yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/yourdomain.com/privkey.pem;
    
    location / {
        proxy_pass http://localhost:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

## 📈 Мониторинг

### Prometheus metrics

FastAPI автоматически экспортирует метрики на `/metrics`

### Grafana dashboard

Импортируйте `monitoring/grafana-dashboard.json`

### Логи

```bash
# Все сервисы
docker compose logs -f

# Конкретный сервис
docker compose logs -f fastapi
docker compose logs -f crawler
docker compose logs -f prefect-server
```

## 🎓 Документация

- **[PIPELINE_GUIDE.md](./PIPELINE_GUIDE.md)** - Детальное руководство
- **[DOCKER_SETUP.md](./DOCKER_SETUP.md)** - Docker конфигурация
- **[SERVER_DEPLOYMENT.md](./SERVER_DEPLOYMENT.md)** - Деплой на сервер
- **[API Documentation](http://localhost:8080/docs)** - Swagger UI

## 🤝 Contributing

Pull requests приветствуются! См. [CONTRIBUTING.md](./CONTRIBUTING.md)

## 📝 License

MIT License - см. [LICENSE](./LICENSE)

## 🙏 Acknowledgments

- [Crawl4AI](https://github.com/unclecode/crawl4ai) - Intelligent crawling
- [ChromaDB](https://www.trychroma.com/) - Vector database
- [Prefect](https://www.prefect.io/) - Workflow orchestration
- [FastAPI](https://fastapi.tiangolo.com/) - Modern API framework
- [DuckDB](https://duckdb.org/) - Analytical database

---

**⭐ Star this repo if you find it useful!**

**🚀 Ready for production with full observability and scalability!**
