# Быстрый старт для финансового консультанта

## 🎯 Что вы получите

За 15 минут настроите систему для:
- Обработки финансовых отчетов (PDF/Excel)
- Сбора данных о компаниях с сайтов
- Анализа и поиска связей в данных
- Семантического поиска по документам

## 📋 Предварительные требования

- Linux/macOS/Windows WSL
- Python 3.11+
- Docker (для PostgreSQL)
- 8 GB RAM минимум
- 20 GB свободного места

## 🚀 Установка за 5 шагов

### Шаг 1: Клонирование и окружение

```bash
# Клонировать проект
git clone https://github.com/leval907/docagent.git /opt/docagent
cd /opt/docagent

# Создать виртуальное окружение
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate   # Windows
```

### Шаг 2: Установка зависимостей

```bash
# Базовая установка (без PyTorch - только DuckDB)
pip install duckdb pandas openpyxl boto3 sentence-transformers

# Полная установка (с Docling - нужен для PDF)
pip install -r requirements.full.txt

# Для веб-краулинга (опционально)
pip install crawl4ai playwright
playwright install chromium --with-deps
```

### Шаг 3: Настройка PostgreSQL

```bash
# Запустить PostgreSQL с pgvector
docker run -d \
  --name postgres-docagent \
  --network opt-network \
  -e POSTGRES_DB=docagent \
  -e POSTGRES_USER=docagent \
  -e POSTGRES_PASSWORD=docagent123 \
  -p 5432:5432 \
  pgvector/pgvector:pg16

# Проверить
docker ps | grep postgres
```

### Шаг 4: Настройка S3 (Beget Cloud)

Создайте файл `.env`:

```bash
cat > .env << 'EOF'
# S3 Storage (Beget)
S3_BUCKET=ваш-bucket-name
S3_ACCESS_KEY=ваш-access-key
S3_SECRET_KEY=ваш-secret-key
S3_ENDPOINT=https://s3.ru1.storage.beget.cloud

# PostgreSQL
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=docagent
POSTGRES_USER=docagent
POSTGRES_PASSWORD=docagent123
EOF
```

### Шаг 5: Проверка работоспособности

```bash
# Тест DuckDB
python scripts/examples/test_duckdb_examples.py

# Тест Docling (если установлен)
python scripts/examples/test_pipeline_full.py
```

## 💼 Практические сценарии

### Сценарий 1: Анализ финансовых таблиц

Есть несколько Excel файлов от клиента с разной структурой.

```python
from scripts.analytics.duckdb_analytics import DuckDBAnalytics

analytics = DuckDBAnalytics()

# Импорт всех Excel из папки
analytics.import_excel("knowledge_base/duckdb/sales_2023.xlsx")
analytics.import_excel("knowledge_base/duckdb/sales_2024.xlsx")
analytics.import_excel("knowledge_base/duckdb/clients.xlsx")

# Посмотреть какие таблицы создались
tables = analytics.list_tables()
print(f"Загружено таблиц: {tables}")

# Автоматически найти связи
relationships = analytics.analyze_relationships()
print("Найденные связи:")
for rel in relationships:
    print(f"  {rel['table1']}.{rel['col1']} ↔ {rel['table2']}.{rel['col2']}")

# Объединить данные
result = analytics.query("""
    SELECT 
        c.company_name,
        c.industry,
        COUNT(s.id) as deals_count,
        SUM(s.amount) as total_revenue,
        AVG(s.amount) as avg_deal_size
    FROM sales_2024 s
    JOIN clients c ON s.client_id = c.id
    GROUP BY c.company_name, c.industry
    ORDER BY total_revenue DESC
""")

# Экспорт результата
analytics.export_to_excel(result, "revenue_analysis_2024.xlsx")
```

**Результат:** Excel файл с консолидированными данными за минуту.

### Сценарий 2: Обработка финансового отчета

Клиент прислал годовой отчет на 200 страниц в PDF.

```python
from scripts.processors.docling_processor import DoclingProcessor

processor = DoclingProcessor()

# Обработать PDF
markdown = processor.process_file(
    "client_annual_report_2024.pdf",
    app_name="client-acme"
)

# Результат:
# ✅ raw/client-acme/client_annual_report_2024.pdf - оригинал в S3
# ✅ processed/client-acme/client_annual_report_2024.md - текст
# ✅ metadata/client-acme/client_annual_report_2024.json - метаданные

# Теперь можно работать с текстом:
# - Поиск ключевых показателей
# - Извлечение таблиц
# - Семантический поиск по разделам
```

**Результат:** Структурированный текст вместо PDF, готов для анализа.

### Сценарий 3: Мониторинг конкурентов

Нужно собрать информацию о 10 конкурентах клиента.

```python
from scripts.processors.crawler_crawl4ai import crawl_website
import asyncio

async def monitor_competitors():
    competitors = [
        "https://competitor1.com",
        "https://competitor2.com",
        "https://competitor3.com",
    ]
    
    for url in competitors:
        print(f"Сбор данных: {url}")
        results = await crawl_website(
            start_url=url,
            max_pages=5,  # главная + 4 страницы
            app_name="competitor-monitoring"
        )
        print(f"  ✅ Собрано страниц: {len(results)}")

asyncio.run(monitor_competitors())

# Результат в S3: crawled/competitor-monitoring/
```

**Результат:** Автоматический сбор данных с сайтов в Markdown формате.

### Сценарий 4: Поиск похожих кейсов

Новый клиент из ритейла, нужно найти похожие проекты.

```python
from sentence_transformers import SentenceTransformer
import psycopg2

# Загрузить модель эмбеддингов
model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')

# Описание нового клиента
query = """
Клиент: сеть продуктовых магазинов, 50 точек
Проблема: оптимизация закупок и снижение неликвида
Бюджет: средний
Срок: 3 месяца
"""

# Получить эмбеддинг
query_embedding = model.encode(query)

# Искать похожие в PostgreSQL
conn = psycopg2.connect(
    host="localhost", database="docagent",
    user="docagent", password="docagent123"
)
cur = conn.cursor()

cur.execute("""
    SELECT 
        project_name,
        description,
        1 - (embedding <=> %s::vector) as similarity
    FROM past_projects
    ORDER BY embedding <=> %s::vector
    LIMIT 5
""", (query_embedding.tolist(), query_embedding.tolist()))

for row in cur.fetchall():
    print(f"{row[0]}: {row[2]:.2%} похожесть")
    print(f"  {row[1][:100]}...")
```

**Результат:** Топ-5 похожих проектов из вашего опыта.

## 🎓 Следующие шаги

1. **Изучите примеры:**
   - `scripts/examples/test_duckdb_examples.py` - работа с данными
   - `scripts/examples/test_pipeline_full.py` - полный пайплайн

2. **Прочитайте документацию:**
   - [DuckDB Integration](DUCKDB_INTEGRATION.md) - SQL аналитика
   - [Docling Integration](DOCLING_INTEGRATION.md) - обработка PDF
   - [Crawl4AI Guide](CRAWL4AI_GUIDE.md) - веб-краулинг

3. **Настройте под себя:**
   - Создайте шаблоны для типовых отчетов
   - Настройте автоматические пайплайны через Prefect
   - Добавьте свои источники данных в `config/sources.yaml`

## ⚠️ Частые проблемы

### DuckDB не видит PostgreSQL

```bash
# Проверьте что расширение установлено
python -c "import duckdb; con = duckdb.connect(); con.execute('INSTALL postgres; LOAD postgres')"
```

### Ошибка при импорте Docling

```bash
# Нужно больше RAM или использовать swap
sudo fallocate -l 4G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
```

### S3 ошибка при загрузке

```bash
# Проверьте credentials в .env
# Beget требует signature_version='s3v4' для чтения
# и 's3' для записи (dual client в config/s3_config.py)
```

## 📞 Поддержка

Вопросы? [Создайте issue](https://github.com/leval907/docagent/issues)

---

**Успешной работы с данными!** 📊💼
