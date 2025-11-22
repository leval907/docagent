# DocAgent - Knowledge Management & Analytics Platform

Интегрированная платформа для финансового консалтинга, объединяющая обработку документов, веб-аналитику, работу с данными и семантический поиск.

## 🎯 Для кого

Платформа создана для финансовых консультантов и аналитиков, работающих с большими объемами:
- Финансовых отчетов и презентаций
- Неструктурированных данных из разных источников
- Аналитических таблиц и баз данных
- Знаний из прошлых проектов

## ⚡ Ключевые возможности

### 1. **Обработка документов** (Docling)
- Конвертация PDF/DOCX/HTML → Markdown
- Извлечение таблиц, графиков, структуры
- Автоматическая загрузка в S3 (Beget Cloud)
- Сохранение метаданных и хэшей файлов

**Применение:** Обработка финансовых отчетов клиентов, контрактов, презентаций

### 2. **Веб-разведка** (Crawl4AI)
- Парсинг сайтов компаний с JavaScript
- Извлечение структурированного контента
- Автоматическое сохранение в S3
- Поддержка многостраничного обхода

**Применение:** Анализ конкурентов, сбор рыночных данных, мониторинг компаний

### 3. **Аналитика данных** (DuckDB)
- Импорт Excel/CSV/JSON без схемы
- Автоматическое определение связей между таблицами
- SQL-запросы к разнородным источникам
- Экспорт в Parquet/CSV/JSON
- **Модуль Finance:** Работа с ОСВ (оборотно-сальдовые ведомости)

**Применение:** Консолидация финансовых данных, поиск зависимостей в датасетах, бухгалтерская отчетность

### 4. **База знаний** (PostgreSQL + pgvector)
- Семантический поиск по документам
- Векторные эмбеддинги (384 измерения)
- Хранение истории обработки
- Аналитические витрины данных

**Применение:** Быстрый поиск похожих кейсов, извлечение инсайтов из прошлого опыта

### 5. **Граф знаний** (ArangoDB, в разработке)
- Связи между компаниями, людьми, проектами
- Граф транзакций и контрактов
- Визуализация сетей влияния

**Применение:** Анализ бенефициаров, поиск скрытых связей

### 6. **Semantic Layer** (Cube.js) 🆕
- Единая модель данных поверх PostgreSQL
- SQL API (Postgres Proxy) для BI-инструментов
- Автоматическая агрегация и кэширование
- Dev Playground для моделирования метрик

**Применение:** Подключение DataLens/Metabase, дашборды, консолидированная отчётность

Enterprise-grade platform for document processing, web intelligence, and data analytics.

## Features

- 📄 **Document Processing**: PDF, DOCX, HTML → Markdown
- 🌐 **Web Crawler**: Extract content from websites
- 📊 **Data Analytics**: Excel, CSV, JSON analysis with DuckDB
- 🔍 **Semantic Search**: Vector-based search with PostgreSQL + pgvector
- 🕸️ **Knowledge Graph**: ArangoDB graph database
- 📈 **Semantic Layer**: Cube.js for BI tools (DataLens, Metabase)
- ⚡ **Workflow Automation**: Prefect orchestration
- 🔗 **REST API**: FastAPI endpoints

## 📁 Структура проекта

```
docagent/
├── docs/                    # Документация
│   ├── QUICK_START.md      # Быстрый старт
│   ├── PIPELINE_GUIDE.md   # Гайд по пайплайнам
│   ├── FINANCIAL_QUICKSTART.md  # Для финансистов
│   └── CUBE_ANALYTICS.md   # Cube.js semantic layer 🆕
├── scripts/
│   ├── processors/         # Обработка данных
│   │   ├── docling_processor.py    # PDF/DOCX → Markdown
│   │   └── crawler_crawl4ai.py     # Веб-краулер
│   ├── analytics/          # Аналитика
│   │   └── duckdb_analytics.py     # Работа с данными
│   ├── finance/            # Финансы (ОСВ)
│   │   ├── import_osv_improved.py  # Импорт ОСВ
│   │   ├── consolidated_report.py  # Сводный отчет
│   │   └── README.md               # Документация
│   └── examples/           # Примеры использования
│       ├── test_pipeline_full.py   # Полный пайплайн
│       └── test_duckdb_examples.py # Примеры DuckDB
├── config/
│   ├── s3_config.py        # Настройки S3 (Beget)
│   └── sources.yaml        # Источники данных
├── mycube-docker/          # Cube.js конфигурация 🆕
│   ├── model/              # Data models (кубы, измерения)
│   └── .cubestore/         # Внутреннее хранилище Cube
└── knowledge_base/
    └── duckdb/             # Локальные данные для аналитики
        └── osv/            # ОСВ данные
```

## 🚀 Быстрый старт

### Установка

```bash
# Клонирование
git clone https://github.com/leval907/docagent.git /opt/docagent
cd /opt/docagent

# Создание виртуального окружения
python3 -m venv venv
source venv/bin/activate

# Установка зависимостей
pip install docling crawl4ai duckdb boto3 playwright sentence-transformers
playwright install chromium --with-deps
```

### Настройка PostgreSQL

```bash
# Запуск контейнера с pgvector
docker run -d \
  --name postgres-docagent \
  -e POSTGRES_DB=docagent \
  -e POSTGRES_USER=docagent \
  -e POSTGRES_PASSWORD=docagent123 \
  -p 5432:5432 \
  pgvector/pgvector:pg16
```

### Настройка S3 (Beget Cloud)

Отредактируй `config/s3_config.py`:
```python
S3_BUCKET = "твой-bucket"
S3_ACCESS_KEY = "твой-access-key"
S3_SECRET_KEY = "твой-secret-key"
S3_ENDPOINT = "https://s3.ru1.storage.beget.cloud"
```

## 💼 Примеры использования

### 1. Обработка финансового отчета

```python
from scripts.processors.docling_processor import DoclingProcessor

processor = DoclingProcessor()

# Обработать PDF отчет
markdown_content = processor.process_file(
    "financial_report_2024.pdf",
    app_name="client-reports"
)

# Файл автоматически загружен в S3:
# - raw/client-reports/financial_report_2024.pdf
# - processed/client-reports/financial_report_2024.md
# - metadata/client-reports/financial_report_2024.json
```

### 2. Сбор данных с сайта компании

```python
from scripts.processors.crawler_crawl4ai import crawl_website

# Собрать информацию о компании
results = await crawl_website(
    start_url="https://company.com",
    max_pages=10,
    app_name="competitor-analysis"
)

# Результаты в S3: crawled/competitor-analysis/
```

### 3. Анализ данных из Excel

```python
from scripts.analytics.duckdb_analytics import DuckDBAnalytics

analytics = DuckDBAnalytics()

# Импорт Excel файлов
analytics.import_excel("sales_2024.xlsx")
analytics.import_excel("clients_database.xlsx")

# Автоматический поиск связей
relationships = analytics.analyze_relationships()

# SQL-запрос к данным
result = analytics.query("""
    SELECT 
        clients.company_name,
        SUM(sales.amount) as total_revenue,
        COUNT(sales.id) as deals_count
    FROM sales 
    JOIN clients ON sales.client_id = clients.id
    GROUP BY clients.company_name
    ORDER BY total_revenue DESC
""")

# Экспорт результата
analytics.export_to_excel(result, "revenue_analysis.xlsx")
```

### 4. Полный пайплайн

```python
# См. scripts/examples/test_pipeline_full.py

# 1. Краулинг → S3
# 2. Docling обработка → S3
# 3. Импорт в DuckDB
# 4. Генерация эмбеддингов
# 5. Сохранение в PostgreSQL
# 6. Построение графа в ArangoDB
```

## 🔧 Технологический стек

- **Python 3.12**
- **Docling 2.61.2** - обработка документов
- **Crawl4AI 0.7.6** - веб-краулинг
- **DuckDB 1.4.1** - OLAP аналитика
- **PostgreSQL 16 + pgvector** - векторная БД
- **ArangoDB** - граф БД (планируется)
- **S3 Beget** - облачное хранилище
- **sentence-transformers** - эмбеддинги

## 📊 Архитектура данных

```
Источники → Обработка → Хранилище → Аналитика → BI
   ↓            ↓            ↓           ↓        ↓
PDF/DOCX    Docling      S3 (raw)    DuckDB   Cube.js
Веб-сайты   Crawl4AI     S3 (proc)   PostgreSQL  ↓
Excel/CSV   Python       S3 (meta)   ArangoDB  DataLens
```

## 📖 Документация

- [Быстрый старт](docs/QUICK_START.md)
- [Гайд по Docling](docs/DOCLING_INTEGRATION.md)
- [Гайд по Crawl4AI](docs/CRAWL4AI_GUIDE.md)
- [Работа с DuckDB](docs/DUCKDB_INTEGRATION.md)
- [Архитектура пайплайнов](docs/PIPELINE_GUIDE.md)
- [Cube.js Analytics](docs/CUBE_ANALYTICS.md) 🆕

## 🤝 Поддержка

Для вопросов и предложений: [создайте issue](https://github.com/leval907/docagent/issues)

## 📄 Лицензия

MIT License - см. [LICENSE](LICENSE)

---

**Создано для финансовых консультантов, работающих с данными** 💼📈

## Documentation

- [Quick Start](docs/QUICK_START.md)
- [System Architecture](SYSTEM_ARCHITECTURE.md)
- [Crawl4AI Guide](docs/CRAWL4AI_GUIDE.md)
- [Pipeline Guide](docs/PIPELINE_GUIDE.md)

## Use Cases

1. **Documentation Hub** - Centralize technical documentation
2. **Data Integration** - Analyze heterogeneous datasets
3. **Knowledge Graph** - Build relationships between data
4. **Semantic Search** - Smart search across knowledge base

## Technology Stack

- **Storage**: S3 (Beget), PostgreSQL + pgvector
- **Analytics**: DuckDB, Cube.js (semantic layer)
- **Graph**: ArangoDB
- **Processing**: Docling, Crawl4AI
- **Automation**: Prefect
- **API**: FastAPI

## License

See [LICENSE](LICENSE)
