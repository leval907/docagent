# 🔗 Интеграция AI Agent + Cube.js

## Обзор архитектуры

```
┌─────────────────┐
│  OSV Excel      │
│  Files          │
└────────┬────────┘
         │
         ↓ ETL Pipeline
┌─────────────────────┐
│  PostgreSQL         │
│  history.osv_detail │
└────────┬────────────┘
         │
         ↓ get_profit_from_OSV.py
┌─────────────────────┐
│  GigaChat (LLM)     │
│  Analyzes & Calcs   │
└────────┬────────────┘
         │
         ↓ Saves JSON
┌─────────────────────┐
│  PostgreSQL         │
│  analytics.profit_v │
└────────┬────────────┘
         │
         ↓ Cube.js Model
┌─────────────────────┐
│  ProfitAndLoss.js   │
│  Semantic Layer     │
└────────┬────────────┘
         │
         ↓ Queries
┌─────────────────────┐
│  DataLens / BI      │
│  Dashboards         │
└─────────────────────┘
```

## Что дает интеграция?

### ✅ Без Cube.js (текущее состояние после агента):
- Данные P&L сохранены в `analytics.profit_v`
- Нужно писать SQL запросы для анализа
- Расчет метрик (margins, EBITDA) дублируется в каждом запросе
- Нет единого API для потребителей

### ✅ С Cube.js (после интеграции):
- **Единая модель данных** - все метрики определены один раз
- **Автоматические расчеты** - gross margin, net margin, EBITDA
- **Унифицированный API** - REST/GraphQL/SQL для всех потребителей
- **Кэширование** - pre-aggregations ускоряют запросы
- **Консистентность** - одинаковые расчеты везде

---

## Шаг 1: Создание Cube.js модели

Модель `ProfitAndLoss.js` уже создана в `/opt/docagent/mycube-docker/model/financial/`

**Ключевые возможности:**

### 📊 Measures (Метрики)

**Базовые метрики:**
- `totalRevenue` - Общая выручка
- `totalCostOfGoods` - Себестоимость
- `totalOverheads` - Накладные расходы

**Рентабельность:**
- `grossProfit` - Валовая прибыль
- `grossProfitMargin` - Валовая маржа %
- `operatingProfit` - Операционная прибыль (EBIT)
- `operatingMargin` - Операционная маржа %
- `netProfit` - Чистая прибыль
- `netMargin` - Чистая маржа %
- `ebitda` - EBITDA
- `ebitdaMargin` - EBITDA маржа %

**Расходы:**
- `totalLeasing` - Лизинг
- `totalInterest` - Проценты
- `totalDepreciation` - Амортизация
- `totalTax` - Налоги
- `totalDividends` - Дивиденды

### 🎯 Segments (Сегменты)

- `profitable` - Прибыльные компании (net profit > 0)
- `unprofitable` - Убыточные компании (net profit <= 0)
- `highMargin` - Высокомаржинальные (gross margin > 30%)
- `hasInterest` - Компании с долгом (interest paid > 0)
- `paysDividends` - Выплачивают дивиденды

### 🔗 Joins (Связи)

- `Companies` - Связь с компаниями через `company_code`

---

## Шаг 2: Запуск Cube.js с новой моделью

### Проверка конфигурации

```bash
# Проверить docker-compose
cat /opt/docagent/mycube-docker/docker-compose.yml

# Если файла нет, создать
cat > /opt/docagent/mycube-docker/docker-compose.yml << 'EOF'
version: '3.8'

services:
  cube:
    image: cubejs/cube:latest
    ports:
      - "4000:4000"   # Cube Playground
      - "15432:15432" # SQL API
    environment:
      - CUBEJS_DEV_MODE=true
      - CUBEJS_DB_TYPE=postgres
      - CUBEJS_DB_HOST=host.docker.internal
      - CUBEJS_DB_PORT=5432
      - CUBEJS_DB_NAME=analytics
      - CUBEJS_DB_USER=analytics_user
      - CUBEJS_DB_PASS=analytics_secure_2025
      - CUBEJS_API_SECRET=cube_secret_key_2025
    volumes:
      - ./model:/cube/conf/model
      - ./.cubestore:/cube/conf/.cubestore
    networks:
      - analytics
    extra_hosts:
      - "host.docker.internal:host-gateway"

networks:
  analytics:
    driver: bridge
EOF
```

### Запуск Cube.js

```bash
cd /opt/docagent/mycube-docker
docker-compose up -d

# Проверка логов
docker-compose logs -f cube
```

Cube.js будет доступен на:
- **Playground**: http://localhost:4000
- **SQL API**: localhost:15432

---

## Шаг 3: Тестирование в Cube Playground

Откройте http://localhost:4000 и попробуйте запросы:

### Запрос 1: Топ компаний по выручке

```javascript
{
  "measures": [
    "ProfitAndLoss.totalRevenue",
    "ProfitAndLoss.grossProfit",
    "ProfitAndLoss.grossProfitMargin"
  ],
  "dimensions": [
    "ProfitAndLoss.companyName"
  ],
  "order": {
    "ProfitAndLoss.totalRevenue": "desc"
  },
  "limit": 10
}
```

### Запрос 2: Прибыльные vs убыточные

```javascript
{
  "measures": [
    "ProfitAndLoss.count",
    "ProfitAndLoss.totalRevenue",
    "ProfitAndLoss.netProfit"
  ],
  "segments": [
    "ProfitAndLoss.profitable"
  ]
}
```

### Запрос 3: Финансовые коэффициенты

```javascript
{
  "measures": [
    "ProfitAndLoss.grossProfitMargin",
    "ProfitAndLoss.operatingMargin",
    "ProfitAndLoss.netMargin",
    "ProfitAndLoss.ebitdaMargin"
  ],
  "dimensions": [
    "ProfitAndLoss.companyName"
  ],
  "filters": [
    {
      "member": "ProfitAndLoss.revenue",
      "operator": "gt",
      "values": ["1000000"]
    }
  ]
}
```

---

## Шаг 4: SQL API для DataLens

Подключение к Cube.js как к PostgreSQL:

```yaml
Host: localhost
Port: 15432
Database: db
Username: cube
Password: cube_secret_key_2025
SSL: disabled
```

### Примеры SQL запросов

```sql
-- Топ 10 компаний по прибыльности
SELECT 
  company_name,
  total_revenue,
  net_profit,
  net_margin
FROM ProfitAndLoss
ORDER BY net_profit DESC
LIMIT 10;

-- Прибыльные компании
SELECT 
  COUNT(*) as companies,
  SUM(total_revenue) as total_revenue,
  SUM(net_profit) as total_net_profit,
  AVG(net_margin) as avg_margin
FROM ProfitAndLoss
WHERE __segment = 'profitable';

-- Компании с долгом
SELECT 
  company_name,
  total_interest,
  total_revenue,
  (total_interest / NULLIF(total_revenue, 0)) * 100 as interest_burden_pct
FROM ProfitAndLoss
WHERE __segment = 'hasInterest'
ORDER BY interest_burden_pct DESC;
```

---

## Шаг 5: REST API для приложений

### Endpoint

```
POST http://localhost:4000/cubejs-api/v1/load
Authorization: Bearer cube_secret_key_2025
Content-Type: application/json
```

### Пример запроса (curl)

```bash
curl -X POST \
  http://localhost:4000/cubejs-api/v1/load \
  -H 'Authorization: Bearer cube_secret_key_2025' \
  -H 'Content-Type: application/json' \
  -d '{
    "query": {
      "measures": [
        "ProfitAndLoss.totalRevenue",
        "ProfitAndLoss.netProfit",
        "ProfitAndLoss.netMargin"
      ],
      "dimensions": [
        "ProfitAndLoss.companyName"
      ],
      "order": {
        "ProfitAndLoss.totalRevenue": "desc"
      },
      "limit": 5
    }
  }'
```

### Пример ответа

```json
{
  "data": [
    {
      "ProfitAndLoss.companyName": "ГРОСС ГРУП ДИ ООО",
      "ProfitAndLoss.totalRevenue": "150000000.50",
      "ProfitAndLoss.netProfit": "25000000.00",
      "ProfitAndLoss.netMargin": "16.67"
    },
    ...
  ]
}
```

---

## Шаг 6: Автоматизация полного пайплайна

Создайте скрипт для полного цикла:

```bash
#!/bin/bash
# full_pipeline.sh - От Excel до Cube.js

set -e

echo "📥 Step 1: Import OSV data from Excel"
python3 scripts/finance/etl/import_osv.py /opt/docagent/data/osv_revenue_0925/input/

echo "🤖 Step 2: Run AI Agent for P&L generation"
companies=(
    "GROSS_GRUP_DI"
    "VAITERA"
    "PARTNER"
    "GLOBALKONSALT"
)

for company in "${companies[@]}"; do
    echo "  Processing $company..."
    python3 scripts/finance/get_profit_from_OSV.py "$company"
    sleep 3
done

echo "♻️ Step 3: Refresh Cube.js cache"
curl -X POST \
  http://localhost:4000/cubejs-api/v1/pre-aggregations/jobs \
  -H "Authorization: Bearer cube_secret_key_2025" \
  -H "Content-Type: application/json" \
  -d '{
    "action": "post",
    "selector": {
      "contexts": [
        {"securityContext": {}}
      ]
    }
  }'

echo "✅ Pipeline complete! Data available in Cube.js"
echo "   Playground: http://localhost:4000"
echo "   SQL API: localhost:15432"
```

Запуск:
```bash
chmod +x full_pipeline.sh
./full_pipeline.sh
```

---

## Шаг 7: Мониторинг и отладка

### Проверка данных в Cube.js

```bash
# Проверить, что модель загружена
curl http://localhost:4000/cubejs-api/v1/meta \
  -H "Authorization: Bearer cube_secret_key_2025" | jq '.cubes[] | select(.name == "ProfitAndLoss")'

# Проверить доступность SQL API
PGPASSWORD=cube_secret_key_2025 psql -h localhost -p 15432 -U cube -d db -c "SHOW CUBES;"
```

### Логи Cube.js

```bash
# Все логи
docker-compose logs -f cube

# Только ошибки
docker-compose logs cube | grep ERROR

# SQL запросы
docker-compose logs cube | grep "SQL"
```

---

## Примеры использования

### Use Case 1: Dashboard в DataLens

1. Подключиться к Cube SQL API (localhost:15432)
2. Создать датасет с запросом:
```sql
SELECT 
  company_name,
  total_revenue,
  gross_profit_margin,
  operating_margin,
  net_margin,
  ebitda_margin
FROM ProfitAndLoss
WHERE total_revenue > 0
```
3. Создать чарты:
   - Bar chart: Revenue by company
   - Scatter: Operating margin vs Revenue
   - Table: Top profitable companies

### Use Case 2: Telegram Bot с финансовыми метриками

```python
import requests

CUBE_API = "http://localhost:4000/cubejs-api/v1/load"
HEADERS = {
    "Authorization": "Bearer cube_secret_key_2025",
    "Content-Type": "application/json"
}

def get_company_metrics(company_name):
    query = {
        "measures": [
            "ProfitAndLoss.totalRevenue",
            "ProfitAndLoss.netProfit",
            "ProfitAndLoss.netMargin"
        ],
        "dimensions": ["ProfitAndLoss.companyName"],
        "filters": [{
            "member": "ProfitAndLoss.companyName",
            "operator": "contains",
            "values": [company_name]
        }]
    }
    
    response = requests.post(CUBE_API, headers=HEADERS, json={"query": query})
    return response.json()["data"][0]

# Использование
metrics = get_company_metrics("ГРОСС ГРУП")
print(f"Revenue: {metrics['ProfitAndLoss.totalRevenue']}")
print(f"Net Profit: {metrics['ProfitAndLoss.netProfit']}")
print(f"Margin: {metrics['ProfitAndLoss.netMargin']}%")
```

### Use Case 3: Excel отчет из Cube.js

```python
import pandas as pd
import requests

response = requests.post(
    "http://localhost:4000/cubejs-api/v1/load",
    headers={"Authorization": "Bearer cube_secret_key_2025"},
    json={
        "query": {
            "measures": [
                "ProfitAndLoss.totalRevenue",
                "ProfitAndLoss.grossProfit",
                "ProfitAndLoss.netProfit"
            ],
            "dimensions": ["ProfitAndLoss.companyName"]
        }
    }
)

df = pd.DataFrame(response.json()["data"])
df.to_excel("/tmp/profit_report.xlsx", index=False)
print("✅ Report saved to /tmp/profit_report.xlsx")
```

---

## Архитектурные преимущества

### 1. Разделение ответственности
- **AI Agent** - Извлечение insights из сырых данных
- **Cube.js** - Семантический слой и агрегации
- **PostgreSQL** - Хранение данных
- **BI Tools** - Визуализация

### 2. Масштабируемость
- Добавление новых метрик - только в Cube.js модели
- Новые агенты пишут в свои таблицы
- Cube.js объединяет всё через joins

### 3. Консистентность
- Одна формула gross margin используется везде
- Изменение расчета - в одном месте
- Нет расхождений между отчетами

### 4. Производительность
- Pre-aggregations кэшируют частые запросы
- SQL API использует кэш Cube.js
- Агенты работают асинхронно

---

## Troubleshooting

### Cube.js не видит таблицу profit_v

**Проблема:**
```
Error: relation "analytics.profit_v" does not exist
```

**Решение:**
```bash
# Проверить, что таблица существует
PGPASSWORD=analytics_secure_2025 psql -h localhost -U analytics_user -d analytics -c "\dt analytics.*"

# Проверить подключение Cube.js к БД
docker-compose logs cube | grep "connection"
```

### Пустые результаты в Cube.js

**Проблема:** Запросы работают, но возвращают []

**Решение:**
```bash
# Проверить данные в таблице
PGPASSWORD=analytics_secure_2025 psql -h localhost -U analytics_user -d analytics -c \
"SELECT COUNT(*) FROM analytics.profit_v;"

# Если 0, запустить агента
python3 scripts/finance/get_profit_from_OSV.py "GROSS_GRUP_DI"
```

### Ошибка "Cannot read property 'sql' of undefined"

**Проблема:** Синтаксическая ошибка в модели

**Решение:**
```bash
# Проверить синтаксис JS
cd /opt/docagent/mycube-docker/model/financial
node -c ProfitAndLoss.js

# Посмотреть логи Cube.js
docker-compose logs cube | grep "ProfitAndLoss"
```

---

## Следующие шаги

1. ✅ Создать модель `ProfitAndLoss.js` - **Готово**
2. ⏳ Запустить Cube.js с новой моделью
3. ⏳ Протестировать запросы в Playground
4. ⏳ Подключить DataLens к SQL API
5. ⏳ Создать дашборд с основными метриками
6. ⏳ Автоматизировать обновление данных (cron)
7. ⏳ Добавить другие агенты (balance sheet, cash flow)

---

**Дата:** 2025-11-24  
**Версия:** 1.0  
**Статус:** Готово к тестированию
