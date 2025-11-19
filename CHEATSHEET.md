# DocAgent - Шпаргалка для финансового консультанта

## 🚀 Быстрые команды

### Активация окружения
```bash
cd /opt/docagent
source venv/bin/activate
```

### Работа с Excel/CSV данными (DuckDB)

```python
from scripts.analytics.duckdb_analytics import DuckDBAnalytics

# Создать аналитику
analytics = DuckDBAnalytics()

# Импорт данных
analytics.import_excel("sales_2024.xlsx")
analytics.import_csv("clients.csv")
analytics.import_json("products.json")

# Автопоиск связей
relationships = analytics.analyze_relationships()

# SQL запрос
result = analytics.query("""
    SELECT 
        clients.name,
        SUM(sales.amount) as revenue
    FROM sales
    JOIN clients ON sales.client_id = clients.id
    GROUP BY clients.name
""")

# Экспорт результата
analytics.export_to_excel(result, "report.xlsx")
analytics.export_to_parquet(result, "report.parquet")
```

### Обработка PDF/DOCX документов (Docling)

```python
from scripts.processors.docling_processor import DoclingProcessor

processor = DoclingProcessor()

# Один файл
markdown = processor.process_file(
    "financial_report.pdf",
    app_name="client-reports"
)

# Целая папка
results = processor.process_directory(
    "inbox/",
    app_name="client-reports"
)

# Результаты автоматически в S3:
# - raw/client-reports/financial_report.pdf
# - processed/client-reports/financial_report.md
# - metadata/client-reports/financial_report.json
```

### Сбор данных с сайтов (Crawl4AI)

```python
from scripts.processors.crawler_crawl4ai import crawl_website
import asyncio

async def crawl():
    results = await crawl_website(
        start_url="https://company.com",
        max_pages=10,
        app_name="competitor-analysis"
    )
    return results

# Запуск
results = asyncio.run(crawl())

# Результаты в S3: crawled/competitor-analysis/
```

## 📊 Работа с финансовыми данными (ОСВ)

### Модуль Finance - ОСВ Консолидация

**Импорт данных ОСВ:**
```bash
cd /opt/docagent
source venv/bin/activate

# Импортировать все ОСВ из Excel
python scripts/finance/import_osv_improved.py

# Создать консолидированный отчет
python scripts/finance/consolidated_report.py
```

**Через DuckDB Analytics:**
```python
from scripts.analytics.duckdb_analytics import DuckDBAnalytics

# Подключиться к базе ОСВ
analytics = DuckDBAnalytics(
    db_path="knowledge_base/duckdb/osv/osv_database.duckdb"
)

# Консолидация по всем компаниям
result = analytics.query("""
    SELECT 
        account_number,
        account_name,
        SUM(debit_turnover) as total_debit,
        SUM(credit_turnover) as total_credit
    FROM osv_data
    GROUP BY account_number, account_name
    ORDER BY account_number
""")

analytics.export_to_excel(result, "consolidated_osv.xlsx")
```

**Подробнее:** `scripts/finance/README.md`

---

## 📊 Типовые сценарии

### Сценарий 1: Консолидация финансовых данных

```python
# У вас есть:
# - sales_q1.xlsx
# - sales_q2.xlsx
# - clients_list.xlsx
# - products_catalog.csv

analytics = DuckDBAnalytics()

# Импорт всех файлов
analytics.import_excel("sales_q1.xlsx")
analytics.import_excel("sales_q2.xlsx") 
analytics.import_excel("clients_list.xlsx")
analytics.import_csv("products_catalog.csv")

# Объединить данные
result = analytics.query("""
    -- Объединяем Q1 и Q2
    WITH all_sales AS (
        SELECT * FROM sales_q1
        UNION ALL
        SELECT * FROM sales_q2
    )
    -- Добавляем информацию о клиентах и продуктах
    SELECT 
        c.company_name,
        c.industry,
        p.product_name,
        p.category,
        COUNT(s.id) as deals,
        SUM(s.amount) as revenue,
        AVG(s.amount) as avg_deal
    FROM all_sales s
    JOIN clients_list c ON s.client_id = c.id
    JOIN products_catalog p ON s.product_id = p.id
    GROUP BY 1, 2, 3, 4
    ORDER BY revenue DESC
""")

# Экспорт
analytics.export_to_excel(result, "h1_2024_revenue_by_client.xlsx")
```

### Сценарий 2: Анализ финансового отчета

```python
# Клиент прислал годовой отчет на 150 страниц

processor = DoclingProcessor()

# Конвертировать в Markdown
markdown = processor.process_file(
    "client_annual_report_2024.pdf",
    app_name="acme-corp"
)

# Теперь можно:
# 1. Искать ключевые показатели регулярками
import re

# Найти выручку
revenue_pattern = r'выручка.*?(\d[\d\s,\.]+)\s*(млн|млрд|тыс)'
revenues = re.findall(revenue_pattern, markdown, re.IGNORECASE)

# 2. Извлечь таблицы
tables = processor.extract_tables(markdown)

# 3. Семантический поиск
# (требуется PostgreSQL + эмбеддинги)
```

### Сценарий 3: Мониторинг конкурентов

```python
# Еженедельный сбор данных с сайтов конкурентов

competitors = [
    ("https://competitor1.com", "competitor-1"),
    ("https://competitor2.com", "competitor-2"),
    ("https://competitor3.com", "competitor-3"),
]

async def monitor_all():
    for url, name in competitors:
        print(f"Обрабатываем {name}...")
        results = await crawl_website(
            start_url=url,
            max_pages=5,
            app_name=f"monitoring/{name}"
        )
        print(f"  ✅ Собрано страниц: {len(results)}")

asyncio.run(monitor_all())

# Результаты:
# - crawled/monitoring/competitor-1/...
# - crawled/monitoring/competitor-2/...
# - crawled/monitoring/competitor-3/...
```

### Сценарий 4: Поиск похожих проектов

```python
# Новый клиент, нужно найти похожие кейсы из опыта

from sentence_transformers import SentenceTransformer
import psycopg2

model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')

# Описание нового клиента
query = """
Ритейл, 50 магазинов, оптимизация закупок,
снижение неликвида, бюджет средний, 3 месяца
"""

# Получить эмбеддинг
query_vec = model.encode(query)

# Искать в PostgreSQL
conn = psycopg2.connect(
    host="localhost",
    database="docagent",
    user="docagent",
    password="docagent123"
)

cur = conn.cursor()
cur.execute("""
    SELECT 
        project_name,
        description,
        1 - (embedding <=> %s::vector) as similarity
    FROM past_projects
    WHERE 1 - (embedding <=> %s::vector) > 0.7
    ORDER BY similarity DESC
    LIMIT 5
""", (query_vec.tolist(), query_vec.tolist()))

for row in cur.fetchall():
    print(f"{row[0]}: {row[2]:.1%} похожесть")
```

## 🔧 Утилиты

### Проверка подключения к PostgreSQL

```bash
docker ps | grep postgres
docker exec -it postgres-docagent psql -U docagent -d docagent -c "\dt"
```

### Проверка S3

```python
from config.s3_config import list_s3_files

# Список файлов в S3
files = list_s3_files(prefix="processed/")
for f in files[:10]:
    print(f)
```

### Очистка DuckDB

```python
analytics = DuckDBAnalytics()

# Список таблиц
tables = analytics.list_tables()
print(f"Таблиц: {len(tables)}")

# Удалить таблицу
analytics.query("DROP TABLE IF EXISTS sales_2023")

# Или создать новую базу
analytics = DuckDBAnalytics(db_path="knowledge_base/duckdb/new_analytics.duckdb")
```

## 📁 Структура S3

```
bucket/
├── raw/                    # Оригинальные файлы
│   └── {app_name}/
│       └── file.pdf
├── processed/              # Обработанные (Markdown)
│   └── {app_name}/
│       └── file.md
├── metadata/               # Метаданные JSON
│   └── {app_name}/
│       └── file.json
└── crawled/               # Данные с сайтов
    └── {app_name}/
        └── page.md
```

## 🔑 Переменные окружения (.env)

```bash
# S3 Storage (Beget)
S3_BUCKET=your-bucket
S3_ACCESS_KEY=your-access-key
S3_SECRET_KEY=your-secret-key
S3_ENDPOINT=https://s3.ru1.storage.beget.cloud

# PostgreSQL
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=docagent
POSTGRES_USER=docagent
POSTGRES_PASSWORD=docagent123
```

## 📚 Полезные ссылки

- [Быстрый старт для финансиста](docs/FINANCIAL_QUICKSTART.md)
- [Гайд по DuckDB](docs/DUCKDB_INTEGRATION.md)
- [Гайд по Docling](docs/DOCLING_INTEGRATION.md)
- [Гайд по Crawl4AI](docs/CRAWL4AI_GUIDE.md)

## 🆘 Частые проблемы

**DuckDB: таблица не найдена**
```python
# Проверьте список таблиц
analytics.list_tables()
```

**Docling: ImportError**
```bash
# Нужен полный стек
pip install -r requirements.full.txt
```

**S3: Access Denied**
```python
# Проверьте credentials в .env
# Для Beget нужны оба signature_version
```

**PostgreSQL: connection refused**
```bash
# Проверьте контейнер
docker ps | grep postgres
# Перезапустите
docker restart postgres-docagent
```

---

**Успешной работы!** 💼📊
