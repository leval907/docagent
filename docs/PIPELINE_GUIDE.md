# Crawl & Clean Pipeline

Единый скрипт для полного цикла обработки документации:
1. **Краулинг** - извлечение контента с помощью Crawl4AI
2. **Очистка** - удаление мусора, форматирование markdown
3. **Upload** - загрузка в S3 (опционально)
4. **Индексация** - сохранение метаданных в PostgreSQL (опционально)

## Быстрый старт

### Минимальная конфигурация (локальное хранилище)

```bash
python scripts/crawl_and_clean.py --app openspg
```

Результат: markdown файлы в `knowledge_base/openspg/`

### С PostgreSQL

```bash
python scripts/crawl_and_clean.py --app openspg \
    --pg-host localhost \
    --pg-database docagent \
    --pg-user postgres \
    --pg-password secret
```

### С S3 и PostgreSQL (полный пайплайн)

```bash
python scripts/crawl_and_clean.py --app openspg \
    --s3-bucket my-docs-bucket \
    --s3-endpoint https://s3.amazonaws.com \
    --pg-host localhost \
    --pg-database docagent \
    --pg-user postgres \
    --pg-password secret
```

### Использование переменных окружения

Создайте `.env` файл:

```bash
cp .env.example .env
# Отредактируйте .env
```

Затем запустите:

```bash
# Загрузка переменных окружения
export $(cat .env | xargs)

# Запуск с переменными из окружения
python scripts/crawl_and_clean.py --app openspg \
    --s3-bucket $S3_BUCKET \
    --s3-endpoint $S3_ENDPOINT
```

## Параметры командной строки

| Параметр | Описание | Обязательный |
|----------|----------|--------------|
| `--app` | ID приложения из `config/sources.yaml` | ✅ |
| `--s3-bucket` | Имя S3 bucket | ❌ |
| `--s3-endpoint` | URL S3 endpoint | ❌ |
| `--s3-access-key` | S3 access key (или `AWS_ACCESS_KEY_ID`) | ❌ |
| `--s3-secret-key` | S3 secret key (или `AWS_SECRET_ACCESS_KEY`) | ❌ |
| `--pg-host` | PostgreSQL host (или `PG_HOST`) | ❌ |
| `--pg-port` | PostgreSQL port (по умолчанию 5432) | ❌ |
| `--pg-database` | PostgreSQL database (или `PG_DATABASE`) | ❌ |
| `--pg-user` | PostgreSQL user (или `PG_USER`) | ❌ |
| `--pg-password` | PostgreSQL password (или `PG_PASSWORD`) | ❌ |

## Структура базы данных

### Таблица `documents`

```sql
CREATE TABLE documents (
    id SERIAL PRIMARY KEY,
    app_id VARCHAR(255) NOT NULL,
    url TEXT NOT NULL UNIQUE,
    title TEXT,
    file_path TEXT,
    s3_path TEXT,
    word_count INTEGER,
    file_hash VARCHAR(64),
    crawled_at TIMESTAMP,
    cleaned_at TIMESTAMP,
    uploaded_at TIMESTAMP,
    metadata JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### Таблица `crawl_stats`

```sql
CREATE TABLE crawl_stats (
    id SERIAL PRIMARY KEY,
    app_id VARCHAR(255) NOT NULL,
    pages_crawled INTEGER,
    pages_cleaned INTEGER,
    pages_uploaded INTEGER,
    total_words INTEGER,
    started_at TIMESTAMP,
    finished_at TIMESTAMP,
    duration_seconds FLOAT,
    status VARCHAR(50)
);
```

## Примеры запросов

### Получить все документы приложения

```sql
SELECT url, title, word_count, crawled_at 
FROM documents 
WHERE app_id = 'openspg' 
ORDER BY crawled_at DESC;
```

### Статистика по всем краулам

```sql
SELECT 
    app_id,
    COUNT(*) as total_crawls,
    SUM(pages_crawled) as total_pages,
    SUM(total_words) as total_words,
    AVG(duration_seconds) as avg_duration
FROM crawl_stats
GROUP BY app_id;
```

### Последний краул каждого приложения

```sql
SELECT DISTINCT ON (app_id)
    app_id,
    pages_crawled,
    total_words,
    finished_at,
    status
FROM crawl_stats
ORDER BY app_id, finished_at DESC;
```

## Настройка PostgreSQL

### Локальная установка

```bash
# Ubuntu/Debian
sudo apt install postgresql postgresql-contrib

# macOS
brew install postgresql
brew services start postgresql

# Создание базы данных
createdb docagent

# Подключение
psql -d docagent
```

### Docker

```bash
docker run -d \
    --name docagent-postgres \
    -e POSTGRES_DB=docagent \
    -e POSTGRES_USER=postgres \
    -e POSTGRES_PASSWORD=secret \
    -p 5432:5432 \
    postgres:16
```

## Настройка S3

### AWS S3

1. Создайте bucket в [AWS Console](https://console.aws.amazon.com/s3/)
2. Создайте IAM пользователя с правами на S3
3. Получите access key и secret key

### MinIO (локальный S3)

```bash
docker run -d \
    --name docagent-minio \
    -p 9000:9000 \
    -p 9001:9001 \
    -e MINIO_ROOT_USER=minioadmin \
    -e MINIO_ROOT_PASSWORD=minioadmin \
    minio/minio server /data --console-address ":9001"
```

Затем создайте bucket через веб-интерфейс: http://localhost:9001

## Примеры использования

### 1. Краул с сохранением только локально

```bash
python scripts/crawl_and_clean.py --app openspg
```

**Результат:**
- ✅ Markdown файлы в `knowledge_base/openspg/`
- ❌ Не загружается в S3
- ❌ Не сохраняется в БД

### 2. Краул + PostgreSQL индекс

```bash
python scripts/crawl_and_clean.py --app nocodb \
    --pg-host localhost \
    --pg-database docagent \
    --pg-user postgres \
    --pg-password secret
```

**Результат:**
- ✅ Markdown локально
- ✅ Индекс в PostgreSQL
- ❌ Не загружается в S3

### 3. Полный пайплайн (Crawl → Clean → S3 → PostgreSQL)

```bash
python scripts/crawl_and_clean.py --app openspg \
    --s3-bucket my-docs \
    --s3-endpoint https://s3.amazonaws.com \
    --pg-host localhost \
    --pg-database docagent \
    --pg-user postgres \
    --pg-password secret
```

**Результат:**
- ✅ Markdown локально
- ✅ Загружено в S3
- ✅ Индекс в PostgreSQL
- ✅ Полная статистика

### 4. Batch processing (несколько сайтов)

```bash
# Обработать все включенные приложения
for app in openspg nocodb; do
    python scripts/crawl_and_clean.py --app $app \
        --s3-bucket my-docs \
        --pg-host localhost \
        --pg-database docagent \
        --pg-user postgres \
        --pg-password secret
done
```

## Мониторинг прогресса

Скрипт выводит подробные логи:

```
======================================================================
🚀 Processing: OpenSPG Documentation
======================================================================
📡 Stage 1: Crawling openspg
  [1/100] Depth 0: https://openspg.yuque.com/ndx6g9/0.8.en
  [2/100] Depth 1: https://openspg.yuque.com/ndx6g9/0.8.en/ka1dw1s1856wmye5
  ...
✅ Crawled 24 pages

🧹 Stage 2: Cleaning & Saving
  Uploaded to S3: openspg/ndx6g9-0.8.en.md
  ...
✅ Cleaned and saved 24 documents

💾 Stage 3: Saving to PostgreSQL
  Saved 24 documents to PostgreSQL

======================================================================
📊 Summary for openspg
======================================================================
  Pages crawled:  24
  Pages cleaned:  24
  Uploaded to S3: 24
  Saved to DB:    24
  Total words:    12,345
  Duration:       127.5s
======================================================================
```

## Устранение неполадок

### Ошибка: "can't connect to PostgreSQL"

```bash
# Проверьте, что PostgreSQL запущен
sudo systemctl status postgresql

# Проверьте подключение
psql -h localhost -U postgres -d docagent
```

### Ошибка: "S3 access denied"

```bash
# Проверьте credentials
aws s3 ls s3://your-bucket --profile your-profile

# Или с явными ключами
export AWS_ACCESS_KEY_ID=your_key
export AWS_SECRET_ACCESS_KEY=your_secret
```

### Ошибка: "Browser timeout" при краулинге

Увеличьте timeout в `crawl_and_clean.py`:

```python
crawl_config = CrawlerRunConfig(
    delay_before_return_html=10.0,  # было 6.0
    page_timeout=180000,  # было 90000
    ...
)
```

## Архитектура

```
┌─────────────────────────────────────────────────────────────┐
│                    crawl_and_clean.py                       │
└─────────────────────────────────────────────────────────────┘
                            │
        ┌───────────────────┼───────────────────┐
        │                   │                   │
        ▼                   ▼                   ▼
┌───────────────┐  ┌───────────────┐  ┌──────────────┐
│   Crawl4AI    │  │ MarkdownClean │  │   Storage    │
│   (Scraping)  │  │  (Filtering)  │  │ (S3 + DB)    │
└───────────────┘  └───────────────┘  └──────────────┘
        │                   │                   │
        ▼                   ▼                   ▼
    Raw HTML          Clean Markdown      Indexed Files
    + Links           + Metadata          + Metadata
```

## Следующие шаги

После обработки документации вы можете:

1. **Построить поисковый индекс** с Elasticsearch/Meilisearch
2. **Создать векторную базу** с Qdrant/Pinecone/Weaviate
3. **Запустить RAG** с LangChain/LlamaIndex
4. **Развернуть API** для поиска по документации

Пример интеграции с Qdrant см. в `examples/qdrant_index.py`
