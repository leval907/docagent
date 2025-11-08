# 🔄 Unified Pipeline Usage Guide

## Основная команда

```bash
python scripts/crawl_and_clean.py --app <APP_ID> [опции]
```

## 🎯 Сценарии использования

### 1. Локальное хранилище (минимум)

```bash
cd DocAgent
python scripts/crawl_and_clean.py --app openspg
```

📂 Результат: `knowledge_base/openspg/*.md`

---

### 2. С PostgreSQL индексом

```bash
python scripts/crawl_and_clean.py --app openspg \
    --pg-host localhost \
    --pg-database docagent \
    --pg-user postgres \
    --pg-password yourpass
```

📊 Результат:
- Markdown локально
- Метаданные в PostgreSQL

---

### 3. Полный пайплайн (S3 + DB)

```bash
python scripts/crawl_and_clean.py --app openspg \
    --s3-bucket my-docs \
    --s3-endpoint https://s3.amazonaws.com \
    --pg-host localhost \
    --pg-database docagent \
    --pg-user postgres \
    --pg-password yourpass
```

☁️ Результат:
- ✅ Markdown локально
- ✅ Загружено в S3
- ✅ Индекс в PostgreSQL

---

## 🐳 Docker Setup

### PostgreSQL

```bash
docker run -d \
    --name docagent-postgres \
    -e POSTGRES_DB=docagent \
    -e POSTGRES_PASSWORD=secret \
    -p 5432:5432 \
    postgres:16
```

### MinIO (S3-compatible)

```bash
docker run -d \
    --name docagent-minio \
    -p 9000:9000 -p 9001:9001 \
    -e MINIO_ROOT_USER=minioadmin \
    -e MINIO_ROOT_PASSWORD=minioadmin \
    minio/minio server /data --console-address ":9001"
```

Веб-интерфейс: http://localhost:9001

---

## 📝 Переменные окружения

Создайте `.env`:

```bash
PG_HOST=localhost
PG_DATABASE=docagent
PG_USER=postgres
PG_PASSWORD=yourpass

AWS_ACCESS_KEY_ID=your_key
AWS_SECRET_ACCESS_KEY=your_secret
S3_BUCKET=my-docs
```

Использование:

```bash
# Linux/Mac
export $(cat .env | xargs)

# Windows PowerShell
Get-Content .env | ForEach-Object {
    if ($_ -match '(.+)=(.+)') {
        $env:($matches[1]) = $matches[2]
    }
}

python scripts/crawl_and_clean.py --app openspg
```

---

## 🔁 Batch обработка

```bash
# Обработать несколько сайтов
for app in openspg nocodb; do
    python scripts/crawl_and_clean.py --app $app \
        --pg-host localhost \
        --pg-database docagent \
        --pg-user postgres \
        --pg-password secret
done
```

---

## 📊 SQL запросы

### Статистика по приложениям

```sql
SELECT app_id, COUNT(*) as docs, 
       SUM(word_count) as words
FROM documents
GROUP BY app_id;
```

### История краулов

```sql
SELECT app_id, pages_crawled, 
       finished_at, status
FROM crawl_stats
ORDER BY finished_at DESC;
```

---

## 🔧 Troubleshooting

**PostgreSQL не подключается:**
```bash
docker logs docagent-postgres
psql -h localhost -U postgres -d docagent
```

**S3 ошибка доступа:**
```bash
aws s3 ls s3://your-bucket
```

**Браузер timeout:**

Отредактируйте `scripts/crawl_and_clean.py`:
```python
crawl_config = CrawlerRunConfig(
    delay_before_return_html=10.0,  # увеличить
    page_timeout=180000,  # увеличить
)
```

---

📖 Полная документация: `PIPELINE_GUIDE.md`
