# 📊 Finance Module - ОСВ Консолидация

Модуль для работы с оборотно-сальдовыми ведомостями (ОСВ) и финансовыми данными.

## 🎯 Назначение

Обработка и консолидация финансовых данных из Excel файлов ОСВ:
- Автоматический импорт из разных форматов
- Консолидация данных по нескольким компаниям
- Генерация сводных отчетов
- Анализ оборотов и остатков

## 📁 Структура

```
scripts/finance/
├── import_osv_improved.py    # Импорт ОСВ из Excel
├── consolidated_report.py    # Сводный отчет
├── analyze_logic.py          # Анализ логики данных
├── consolidate.py            # Консолидация
├── explore_all_osv.py        # Исследование всех ОСВ
├── explore_data.py           # Исследование данных
├── export.py                 # Экспорт результатов
├── find_all_osv.py          # Поиск файлов ОСВ
├── import_osv.py            # Базовый импорт
├── import_summary.py        # Сводка импорта
└── config.yaml              # Конфигурация

knowledge_base/duckdb/osv/
├── osv_database.duckdb      # База данных DuckDB
└── files/                   # Симлинк → /opt/1_Project_Alayns/files/
    ├── Грандпром/
    ├── Гросс групп_ДИ/
    ├── Гросс групп_М/
    ├── Договора_Заказчик_Подрядчик/
    ├── СГК_Регион/
    └── Юг истейт/
```

## 🚀 Использование

### 1. Импорт данных из Excel

```bash
cd /opt/docagent
source venv/bin/activate

# Импортировать все ОСВ
python scripts/finance/import_osv_improved.py
```

**Что делает:**
- Сканирует папки в `knowledge_base/duckdb/osv/files/`
- Находит Excel файлы с ОСВ
- Импортирует в DuckDB (`osv_database.duckdb`)
- Создает таблицы для каждой компании

### 2. Создание консолидированного отчета

```bash
# Сгенерировать сводный отчет
python scripts/finance/consolidated_report.py
```

**Результат:**
- `consolidated_analysis.xlsx` - сводная таблица
- Обороты и остатки по всем компаниям
- Агрегированные показатели

### 3. Исследование данных

```bash
# Просмотр всех таблиц в базе
python scripts/finance/explore_all_osv.py

# Детальное исследование данных
python scripts/finance/explore_data.py
```

### 4. Поиск файлов ОСВ

```bash
# Найти все Excel файлы с ОСВ
python scripts/finance/find_all_osv.py
```

## 📊 Работа через DuckDB Analytics

Можно использовать общий `duckdb_analytics.py` для работы с ОСВ:

```python
from scripts.analytics.duckdb_analytics import DuckDBAnalytics

# Подключиться к базе ОСВ
analytics = DuckDBAnalytics(
    db_path="knowledge_base/duckdb/osv/osv_database.duckdb"
)

# Список всех таблиц (компаний)
tables = analytics.list_tables()
print(f"Компаний в базе: {len(tables)}")

# SQL запрос к данным
result = analytics.query("""
    SELECT 
        company,
        SUM(debit) as total_debit,
        SUM(credit) as total_credit,
        SUM(debit - credit) as balance
    FROM all_companies
    GROUP BY company
    ORDER BY total_debit DESC
""")

# Экспорт в Excel
analytics.export_to_excel(result, "osv_summary.xlsx")
```

## ⚙️ Конфигурация

Файл `config.yaml`:

```yaml
# Путь к данным
data_path: ../../knowledge_base/duckdb/osv/files

# Путь к базе данных
database_path: ../../knowledge_base/duckdb/osv/osv_database.duckdb

# Настройки импорта
import:
  recursive: true          # Рекурсивный поиск файлов
  extensions: [.xlsx, .xls]
  encoding: utf-8

# Компании для обработки
companies:
  - Грандпром
  - Гросс групп_ДИ
  - Гросс групп_М
  - СГК_Регион
  - Юг истейт
```

## 📈 Типовые задачи

### Консолидация оборотов по всем компаниям

```python
analytics = DuckDBAnalytics(db_path="knowledge_base/duckdb/osv/osv_database.duckdb")

result = analytics.query("""
    SELECT 
        account_number,
        account_name,
        SUM(opening_debit) as total_opening_debit,
        SUM(opening_credit) as total_opening_credit,
        SUM(debit_turnover) as total_debit_turnover,
        SUM(credit_turnover) as total_credit_turnover,
        SUM(closing_debit) as total_closing_debit,
        SUM(closing_credit) as total_closing_credit
    FROM osv_data
    GROUP BY account_number, account_name
    ORDER BY account_number
""")

analytics.export_to_excel(result, "consolidated_osv.xlsx")
```

### Анализ задолженности по контрагентам

```python
result = analytics.query("""
    SELECT 
        counterparty,
        SUM(CASE WHEN account_number LIKE '62%' THEN closing_debit ELSE 0 END) as receivables,
        SUM(CASE WHEN account_number LIKE '60%' THEN closing_credit ELSE 0 END) as payables,
        SUM(closing_debit - closing_credit) as net_position
    FROM osv_data
    WHERE account_number LIKE '60%' OR account_number LIKE '62%'
    GROUP BY counterparty
    HAVING ABS(net_position) > 1000
    ORDER BY ABS(net_position) DESC
""")
```

### Сравнение данных по периодам

```python
result = analytics.query("""
    SELECT 
        period,
        COUNT(DISTINCT company) as companies_count,
        SUM(debit_turnover) as total_debit,
        SUM(credit_turnover) as total_credit,
        SUM(debit_turnover - credit_turnover) as net_change
    FROM osv_data
    GROUP BY period
    ORDER BY period
""")
```

## 🔄 Интеграция с основным DocAgent

Модуль finance интегрирован с основным DocAgent:

- ✅ Использует общий DuckDB движок
- ✅ Работает в едином venv
- ✅ Доступен через общий API (если нужно)
- ✅ Может использоваться в Streamlit UI

## 📝 Примечания

- База данных `osv_database.duckdb` находится в `knowledge_base/duckdb/osv/`
- Исходные файлы не копируются, используется симлинк на `/opt/1_Project_Alayns/files/`
- Все скрипты адаптированы для работы с относительными путями от `/opt/docagent`

## 🆘 Решение проблем

**Ошибка: файлы не найдены**
```bash
# Проверьте симлинк
ls -la knowledge_base/duckdb/osv/files/
```

**Ошибка: база данных не найдена**
```bash
# Проверьте наличие БД
ls -lh knowledge_base/duckdb/osv/osv_database.duckdb
```

**Ошибка: ModuleNotFoundError**
```bash
# Убедитесь что venv активирован
source venv/bin/activate
pip list | grep -E "duckdb|pandas|openpyxl"
```

---

**Готово к работе!** 🚀
