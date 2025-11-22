# Cube.js Analytics - Semantic Layer для финансовой аналитики

## 🎯 Что такое Cube.js?

Cube.js — это semantic layer (семантический слой) над PostgreSQL, который предоставляет:
- 📊 Единую модель данных (кубы, измерения, метрики)
- 🔄 Автоматическую агрегацию и кэширование
- 🔌 SQL API (Postgres Proxy) для BI-инструментов
- 🎨 Dev Playground для моделирования
- 📈 REST/GraphQL API для дашбордов

**Для финансистов:** Cube.js позволяет работать с финансовыми данными на уровне бизнес-метрик (обороты, сальдо, ДДС) без написания сложных SQL-запросов.

---

## 🚀 Установка и запуск

### Быстрый старт

```bash
# Переход в директорию проекта
cd /opt/docagent

# Создание папки для Cube.js конфигурации
mkdir -p mycube-docker
cd mycube-docker

# Запуск контейнера
docker run -d \
  --name cube-analytics \
  --network opt-network \
  -p 4000:4000 \
  -p 15432:15432 \
  -v ${PWD}:/cube/conf \
  -e CUBEJS_DEV_MODE=true \
  -e CUBEJS_DB_TYPE=postgres \
  -e CUBEJS_DB_HOST=postgres16 \
  -e CUBEJS_DB_NAME=analytics \
  -e CUBEJS_DB_USER=analytics_user \
  -e CUBEJS_DB_PASS=analytics_secure_2025 \
  -e CUBEJS_DB_PORT=5432 \
  --restart unless-stopped \
  cubejs/cube
```

### Порты и доступ

- **Dev Playground**: http://localhost:4000
  - Интерфейс для создания data models
  - Тестирование запросов
  - Генерация схем
  
- **SQL API (Postgres Proxy)**: localhost:15432
  - Подключение BI-инструментов (DataLens, Metabase, Tableau)
  - Работа через стандартный Postgres протокол
  - Автоматическая оптимизация запросов

---

## 📊 Структура данных PostgreSQL

Cube.js подключается к базе `analytics` со следующими схемами:

### 1. **master** - Справочники
```sql
master.companies          -- Компании группы (23)
master.chart_of_accounts  -- План счетов (206)
master.counterparties     -- Контрагенты (1206)
master.dds_items          -- Статьи ДДС
master.cost_items         -- Статьи затрат
master.periods            -- Периоды отчётности
```

### 2. **history** - Транзакционные данные
```sql
history.osv_detail           -- Детализация ОСВ (4947 записей)
  - detail_level: 0 (агрегат), 1 (аналитика1), 2 (аналитика2)
  
history.cashflow_movements   -- Движения ДДС (390 записей)
history.revenue_analysis     -- Анализ выручки
```

### 3. **analytics** - Витрины данных (Materialized Views)
```sql
analytics.consolidated_balances  -- Сводные балансы по компаниям
analytics.top_debtors            -- Топ дебиторов
analytics.top_creditors          -- Топ кредиторов
analytics.cashflow_summary       -- Сводка по ДДС
```

### 4. **audit** - Аудит и логи
```sql
audit.upload_log            -- История загрузок
audit.data_quality_checks   -- Проверки качества данных
```

---

## 🛠️ Создание Data Models

### Пример 1: Куб "Обороты и Сальдо"

Создайте файл `/opt/docagent/mycube-docker/model/cubes/osv_detail.js`:

```javascript
cube('OsvDetail', {
  sql: `SELECT * FROM history.osv_detail`,
  
  joins: {
    Companies: {
      relationship: 'belongsTo',
      sql: `${CUBE}.company_id = ${Companies}.id`
    },
    
    ChartOfAccounts: {
      relationship: 'belongsTo',
      sql: `${CUBE}.account_code = ${ChartOfAccounts}.account_code`
    },
    
    Counterparties: {
      relationship: 'belongsTo',
      sql: `${CUBE}.counterparty_id = ${Counterparties}.id`
    }
  },
  
  dimensions: {
    id: {
      sql: 'id',
      type: 'number',
      primaryKey: true
    },
    
    companyName: {
      sql: `${Companies}.full_name`,
      type: 'string'
    },
    
    accountCode: {
      sql: 'account_code',
      type: 'string'
    },
    
    accountName: {
      sql: `${ChartOfAccounts}.account_name`,
      type: 'string'
    },
    
    counterpartyName: {
      sql: `${Counterparties}.name`,
      type: 'string'
    },
    
    period: {
      sql: 'period',
      type: 'string'
    },
    
    detailLevel: {
      sql: 'detail_level',
      type: 'number',
      title: 'Уровень детализации'
    },
    
    reportDate: {
      sql: 'report_date',
      type: 'time'
    }
  },
  
  measures: {
    count: {
      type: 'count'
    },
    
    openingDebit: {
      sql: 'opening_debit',
      type: 'sum',
      format: 'currency'
    },
    
    openingCredit: {
      sql: 'opening_credit',
      type: 'sum',
      format: 'currency'
    },
    
    turnoverDebit: {
      sql: 'turnover_debit',
      type: 'sum',
      format: 'currency'
    },
    
    turnoverCredit: {
      sql: 'turnover_credit',
      type: 'sum',
      format: 'currency'
    },
    
    closingDebit: {
      sql: 'closing_debit',
      type: 'sum',
      format: 'currency'
    },
    
    closingCredit: {
      sql: 'closing_credit',
      type: 'sum',
      format: 'currency'
    },
    
    netTurnover: {
      sql: 'turnover_debit - turnover_credit',
      type: 'number',
      format: 'currency'
    }
  },
  
  preAggregations: {
    // Агрегация по компаниям и периодам
    byCompanyPeriod: {
      measures: [
        CUBE.openingDebit,
        CUBE.openingCredit,
        CUBE.turnoverDebit,
        CUBE.turnoverCredit,
        CUBE.closingDebit,
        CUBE.closingCredit
      ],
      dimensions: [
        CUBE.companyName,
        CUBE.period
      ],
      timeDimension: CUBE.reportDate,
      granularity: 'month'
    }
  }
});
```

### Пример 2: Справочник компаний

Создайте файл `/opt/docagent/mycube-docker/model/cubes/companies.js`:

```javascript
cube('Companies', {
  sql: `SELECT * FROM master.companies WHERE is_active = true`,
  
  dimensions: {
    id: {
      sql: 'id',
      type: 'number',
      primaryKey: true
    },
    
    fullName: {
      sql: 'full_name',
      type: 'string',
      title: 'Название компании'
    },
    
    shortName: {
      sql: 'short_name',
      type: 'string'
    },
    
    inn: {
      sql: 'inn',
      type: 'string',
      title: 'ИНН'
    },
    
    ogrn: {
      sql: 'ogrn',
      type: 'string',
      title: 'ОГРН'
    },
    
    legalAddress: {
      sql: 'legal_address',
      type: 'string'
    },
    
    ceo: {
      sql: 'ceo',
      type: 'string',
      title: 'Генеральный директор'
    }
  },
  
  measures: {
    count: {
      type: 'count',
      title: 'Количество компаний'
    }
  }
});
```

### Пример 3: Витрина "Консолидированные балансы"

Создайте файл `/opt/docagent/mycube-docker/model/cubes/consolidated_balances.js`:

```javascript
cube('ConsolidatedBalances', {
  sql: `SELECT * FROM analytics.consolidated_balances`,
  
  joins: {
    Companies: {
      relationship: 'belongsTo',
      sql: `${CUBE}.company_id = ${Companies}.id`
    }
  },
  
  dimensions: {
    companyName: {
      sql: `${Companies}.full_name`,
      type: 'string'
    },
    
    period: {
      sql: 'period',
      type: 'string'
    },
    
    reportDate: {
      sql: 'report_date',
      type: 'time'
    }
  },
  
  measures: {
    totalDebit: {
      sql: 'total_debit',
      type: 'sum',
      format: 'currency',
      title: 'Итого дебет'
    },
    
    totalCredit: {
      sql: 'total_credit',
      type: 'sum',
      format: 'currency',
      title: 'Итого кредит'
    },
    
    recordCount: {
      sql: 'record_count',
      type: 'sum'
    }
  }
});
```

---

## 🔌 Подключение BI-инструментов

### DataLens (Yandex)

1. В DataLens создайте подключение типа **PostgreSQL**
2. Параметры:
   ```
   Host: ваш-сервер-ip
   Port: 15432
   Database: analytics  (любое имя, Cube игнорирует это)
   User: cube
   Password: <API_SECRET из логов Cube>
   ```

3. Выберите таблицы (кубы) для визуализации

### Metabase

1. Добавьте базу данных: **PostgreSQL**
2. Параметры подключения:
   ```
   Host: localhost (или удалённый IP)
   Port: 15432
   Database name: analytics
   Username: cube
   Password: <API_SECRET>
   ```

### Excel / Power BI

Используйте драйвер PostgreSQL ODBC:
- Server: localhost:15432
- Database: analytics
- Auth: cube / <API_SECRET>

---

## 📈 Примеры запросов

### Через REST API

```bash
# Получить обороты по компаниям за период
curl http://localhost:4000/cubejs-api/v1/load \
  -H "Authorization: <API_SECRET>" \
  -G \
  --data-urlencode 'query={
    "measures": ["OsvDetail.turnoverDebit", "OsvDetail.turnoverCredit"],
    "dimensions": ["OsvDetail.companyName", "OsvDetail.period"]
  }'
```

### Через SQL API (psql)

```bash
# Подключение через psql
PGPASSWORD=<API_SECRET> psql -h localhost -p 15432 -U cube -d analytics

# Запрос
SELECT 
  company_name,
  period,
  SUM(turnover_debit) as total_debit,
  SUM(turnover_credit) as total_credit
FROM osv_detail
GROUP BY company_name, period
ORDER BY company_name, period;
```

### Через Python

```python
import psycopg2

conn = psycopg2.connect(
    host='localhost',
    port=15432,
    database='analytics',
    user='cube',
    password='<API_SECRET>'
)

cursor = conn.cursor()
cursor.execute("""
    SELECT 
        company_name,
        SUM(turnover_debit) - SUM(turnover_credit) as net_turnover
    FROM osv_detail
    WHERE period = '9_months_2025'
    GROUP BY company_name
    ORDER BY net_turnover DESC
    LIMIT 10
""")

for row in cursor.fetchall():
    print(f"{row[0]}: {row[1]:,.2f} ₽")
```

---

## 🎨 Dev Playground

Откройте http://localhost:4000 для:

1. **Build** - создание и редактирование data models (кубов)
2. **Schema** - просмотр схемы PostgreSQL
3. **Playground** - интерактивное тестирование запросов
4. **Rollup Designer** - настройка pre-aggregations для ускорения

---

## ⚙️ Управление контейнером

```bash
# Просмотр логов
docker logs cube-analytics -f

# Перезапуск
docker restart cube-analytics

# Остановка
docker stop cube-analytics

# Удаление
docker stop cube-analytics && docker rm cube-analytics
```

---

## 🔧 Полезные функции

### Автоматическое обновление витрин

Cube.js работает напрямую с PostgreSQL, но можно настроить автообновление materialized views:

```sql
-- Функция обновления всех аналитических витрин
SELECT refresh_all_analytics();
```

Добавьте в cron или Prefect flow для регулярного обновления.

### Pre-Aggregations

Для ускорения тяжёлых запросов используйте pre-aggregations в моделях кубов (см. примеры выше). Cube.js автоматически создаст агрегированные таблицы.

---

## 📚 Дополнительные ресурсы

- [Официальная документация Cube.js](https://cube.dev/docs)
- [Data Schema Reference](https://cube.dev/docs/schema/reference/cube)
- [SQL API Guide](https://cube.dev/docs/backend/sql)
- [REST API Reference](https://cube.dev/docs/rest-api)

---

## 🎯 Use Cases для финансовой аналитики

1. **Консолидированная отчётность**
   - Сводка по всем компаниям группы
   - Обороты, сальдо, ДДС
   - Drill-down до контрагента

2. **Анализ дебиторской/кредиторской задолженности**
   - Топ дебиторов/кредиторов
   - Динамика по периодам
   - Просроченная задолженность

3. **Cash Flow анализ**
   - Поступления/платежи по статьям ДДС
   - План-факт анализ
   - Прогнозирование кассовых разрывов

4. **Интеграция с DataLens**
   - Автоматические дашборды
   - Еженедельная отчётность
   - Мобильный доступ

---

**Создано для финансовой аналитики группы компаний** 💼📊
