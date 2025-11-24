# Справочники Master Schema

## Обзор

Master schema содержит 5 основных справочников для финансовой аналитики:

1. **План счетов** (416 счетов) — с группами ликвидности и классификацией
2. **Справочник ДДС** (72 статьи) — категории движения денежных средств
3. **Справочник затрат** (167 статей) — постоянные и переменные затраты
4. **Классификатор ОКВЭД 2** (2818 кодов) — виды экономической деятельности
5. **Коды отчетности РСБУ** (177 кодов) — строки бухгалтерских форм

**Итого:** 5276 строк данных, 17 таблиц, 6 представлений

---

## 1. План счетов (Chart of Accounts)

### Структура

```sql
master.chart_of_accounts
```

**416 счетов** с расширенными атрибутами для анализа баланса и финансовых потоков.

### Основные поля

| Поле | Тип | Описание |
|------|-----|----------|
| `account_code` | VARCHAR | Код счета (01, 10, 50.01 и т.д.) |
| `account_name` | VARCHAR | Название счета |
| `account_level` | INTEGER | Уровень в иерархии (1, 2, 3) |
| `parent_code` | VARCHAR | Родительский счет |
| `balance_flag` | BOOLEAN | Балансовый счет |
| `pnl_flag` | BOOLEAN | Счет прибылей/убытков |
| `liquidity_group` | VARCHAR(2) | Группа ликвидности (A1-A4, P1-P4) |
| `rsbu_type` | VARCHAR | Тип по РСБУ |

### Группы ликвидности

**Активы (189 счетов):**
- **A1** (24 счета) — Высоколиквидные (ДС, краткосрочные вложения)
- **A2** (78 счетов) — Быстрореализуемые (дебиторка до 12 мес)
- **A3** (52 счета) — Медленнореализуемые (запасы, НДС)
- **A4** (35 счетов) — Труднореализуемые (ВНА, долгосрочные вложения)

**Пассивы (132 счета):**
- **P1** (72 счета) — Наиболее срочные (кредиторка)
- **P2** (13 счетов) — Краткосрочные (кредиты до 12 мес)
- **P3** (13 счетов) — Долгосрочные (кредиты > 12 мес)
- **P4** (34 счета) — Постоянные (капитал, прибыль)

### Примеры запросов

```sql
-- Все счета денежных средств
SELECT account_code, account_name 
FROM master.chart_of_accounts
WHERE liquidity_group = 'A1';

-- Балансовые счета по группам ликвидности
SELECT liquidity_group, COUNT(*) 
FROM master.chart_of_accounts
WHERE balance_flag = TRUE
GROUP BY liquidity_group
ORDER BY liquidity_group;
```

### ETL

```bash
python3 scripts/finance/etl/update_chart_of_accounts.py
```

**Источник:** `chart_of_accounts_master_structured_3.xlsx`

---

## 2. Справочник ДДС (Cash Flow Categories)

### Структура

Иерархическая структура с нормализацией:

```
master.dds_categories (7)
  ↓
master.dds_groups (31)
  ↓
master.dds_items (72 уникальных)
  ↓
master.dds_items_mapping (73 варианта интерпретаций)
```

### Категории ДДС

| Код | Название | Статей |
|-----|----------|--------|
| OPS_IN | Операционные поступления | 8 |
| OPS_OUT | Операционные платежи | 18 |
| INV_IN | Инвестиционные поступления | 6 |
| INV_OUT | Инвестиционные платежи | 10 |
| FIN_IN | Финансовые поступления | 7 |
| FIN_OUT | Финансовые платежи | 11 |
| TRF | Трансферты (внутригрупповые) | 12 |

### Представление

```sql
-- Полная иерархия с расшифровками
SELECT * FROM master.v_dds_full_hierarchy;
```

### Примеры запросов

```sql
-- Все операционные статьи
SELECT code, name, group_name
FROM master.dds_items i
JOIN master.dds_categories c ON i.category_id = c.id
WHERE c.code IN ('OPS_IN', 'OPS_OUT');

-- Поиск статьи с учетом вариантов
SELECT item_code, item_name, interpretation
FROM master.dds_items_mapping
WHERE interpretation ILIKE '%займ%';
```

### ETL

```bash
python3 scripts/finance/etl/load_dds_from_excel.py
```

**Источник:** `dds_final_v3_corrected.xlsx` (73 записи с дубликатами)

---

## 3. Справочник затрат (Cost Categories)

### Структура

```
master.cost_categories (2)
  ↓
master.cost_groups (11)
  ↓
master.cost_items (167)
  ↓
master.cost_items_mapping (167 старых кодов)
```

### Категории

| Код | Название | Статей | Описание |
|-----|----------|--------|----------|
| FIX | Постоянные затраты | 150 | Не зависят от объема производства |
| VAR | Переменные затраты | 17 | Зависят от объема производства |

### Группы затрат

1. **Амортизация** (FIX)
2. **IT и связь** (FIX)
3. **Аренда** (FIX)
4. **Ремонт и обслуживание** (FIX)
5. **Охрана** (FIX)
6. **Коммунальные услуги** (FIX)
7. **Налоги и сборы** (FIX)
8. **Заработная плата** (FIX/VAR)
9. **Материалы** (VAR)
10. **Прочие операционные** (FIX/VAR)
11. **Финансовые расходы** (FIX)

### Примеры запросов

```sql
-- Все постоянные затраты
SELECT code, name, group_name
FROM master.cost_items i
JOIN master.cost_categories c ON i.category_id = c.id
WHERE c.code = 'FIX'
ORDER BY group_name, code;

-- Поиск по старому коду
SELECT new_code, new_name, old_name
FROM master.cost_items_mapping
WHERE old_code = 'OLD_123';
```

### ETL

```bash
python3 scripts/finance/etl/load_cost_from_csv.py
```

**Источники:**
- `master_schema_files/cost_categories.csv`
- `master_schema_files/cost_groups.csv`
- `master_schema_files/cost_items.csv`

---

## 4. Классификатор ОКВЭД 2

### Структура

```sql
master.okved (2818 кодов)
```

**6-уровневая иерархия:**

```
Раздел (буква)      → 21 код     A, B, C...
  ↓
Класс (XX)          → 88 кодов   01, 62, 95...
  ↓
Подкласс (XX.X)     → 272 кода   01.1, 62.0...
  ↓
Группа (XX.XX)      → 623 кода   01.11, 62.01...
  ↓
Подгруппа (XX.XX.X) → 1190 кодов 01.11.1...
  ↓
Вид (XX.XX.XX)      → 624 кода   01.11.11...
```

### Связь с компаниями

```sql
master.companies.primary_okved → master.okved.code
master.companies_okved (для множественных видов деятельности)
master.counterparties_okved (для контрагентов)
```

### Представления

```sql
-- Иерархия с полными путями
master.v_okved_hierarchy

-- Компании с расшифровкой ОКВЭД
master.v_companies_with_okved

-- Контрагенты с расшифровкой ОКВЭД
master.v_counterparties_with_okved
```

### Примеры запросов

```sql
-- IT-компании (раздел J, класс 62)
SELECT company_name, primary_okved, primary_okved_name
FROM master.v_companies_with_okved
WHERE primary_section = 'J';

-- Полная иерархия кода
SELECT code, level, name, path_codes
FROM master.v_okved_hierarchy
WHERE code = '62.01';

-- Распределение компаний по отраслям
SELECT 
    o.section,
    os.name AS section_name,
    COUNT(*) AS company_count
FROM master.companies c
JOIN master.okved o ON c.primary_okved = o.code
LEFT JOIN master.okved os ON o.section = os.code AND os.level = 1
GROUP BY o.section, os.name
ORDER BY company_count DESC;
```

### Статистика (компании группы)

| Раздел | Название | Компаний | % |
|--------|----------|----------|---|
| L | Операции с недвижимостью | 11 | 48% |
| M | Профессиональная деятельность | 6 | 26% |
| J | Информация и связь | 2 | 9% |
| F | Строительство | 2 | 9% |

**Покрытие:** 23/23 компании (100%)

### ETL

```bash
# Загрузка справочника
python3 scripts/finance/etl/load_okved.py

# Миграция существующих данных
python3 scripts/finance/etl/migrate_okved.py
```

**Источник:** `okved_2.xls` (версия 02.2022)

**Документация:** [OKVED_INTEGRATION.md](OKVED_INTEGRATION.md)

---

## 5. Коды отчетности РСБУ

### Структура

```sql
master.rsbu_codes (177 кодов)
```

**Формы бухгалтерской отчетности:**

| Форма | Название | Кодов |
|-------|----------|-------|
| БАЛАНС | Бухгалтерский баланс | 37 |
| ОФР | Отчет о финансовых результатах | 26 |
| ОДК | Отчет о движении денежных средств | 41 |
| ОИК | Отчет об изменениях капитала | 50 |
| ОЦИ | Отчет о целевом использовании средств | 23 |

### Поля

| Поле | Описание |
|------|----------|
| `code` | Код строки (1100, 1150, 2110 и т.д.) |
| `name` | Название строки |
| `form` | Форма (БАЛАНС, ОФР, ОДК, ОИК, ОЦИ) |
| `section` | Раздел (АКТИВ, ПАССИВ, КАПИТАЛ...) |
| `row_type` | СТАТЬЯ, ИТОГО, РЕЗУЛЬТАТ, САЛЬДО |
| `is_calculated` | Расчетная строка (TRUE для итогов) |

### Типы строк

| Тип | Количество | Описание |
|-----|------------|----------|
| СТАТЬЯ | 131 | Детальные показатели |
| РЕЗУЛЬТАТ | 23 | Результирующие (прибыль, убыток) |
| ИТОГО | 19 | Промежуточные итоги |
| САЛЬДО | 4 | Сальдо (для ОДК) |

### Маппинг на счета

```sql
master.account_rsbu_mapping
```

**105 связей:** счета плана счетов → строки РСБУ (25% покрытие)

### Представления

```sql
-- Полный маппинг с расшифровками
master.v_account_rsbu_mapping

-- Счета без маппинга (311 счетов, 74%)
master.v_accounts_without_rsbu

-- Строки РСБУ без счетов (122 строки, 93%)
master.v_rsbu_without_accounts
```

### Примеры маппинга

| Счет | Название счета | → | Код РСБУ | Строка отчетности |
|------|----------------|---|----------|-------------------|
| 01 | Основные средства | → | 1150 | Основные средства |
| 10 | Материалы | → | 1210 | Запасы |
| 50-55 | Денежные средства | → | 1250 | Денежные средства |
| 60 | Расчеты с поставщиками | → | 1520 | Кредиторская задолженность |
| 62 | Расчеты с покупателями | → | 1230 | Дебиторская задолженность |
| 90.1 | Выручка | → | 2110 | Выручка |
| 90.2 | Себестоимость | → | 2120 | Себестоимость продаж |

### Примеры запросов

```sql
-- Все строки баланса (Актив)
SELECT code, name, row_type
FROM master.rsbu_codes
WHERE form = 'БАЛАНС' AND section = 'АКТИВ'
ORDER BY code;

-- Маппинг счетов денежных средств
SELECT 
    account_code,
    account_name,
    rsbu_code,
    rsbu_name
FROM master.v_account_rsbu_mapping
WHERE account_code ~ '^(50|51|52|55)';

-- Счета без маппинга (требуют настройки)
SELECT account_code, account_name, liquidity_group
FROM master.v_accounts_without_rsbu
WHERE balance_flag = TRUE
ORDER BY account_code;
```

### ETL

```bash
# Загрузка справочника
python3 scripts/finance/etl/load_rsbu_codes.py

# Создание базового маппинга
psql -h localhost -U analytics_user -d analytics -f sql/rsbu_mapping.sql
```

**Источник:** `account_codes.xls` (177 строк)

---

## Интеграция с Cube.js

Все справочники готовы для использования в Cube.js для создания семантического слоя.

### Примеры dimensions

```javascript
// ОКВЭД
okvedSection: {
  sql: `${okved}.section`,
  type: 'string',
  title: 'Раздел ОКВЭД'
},

okvedName: {
  sql: `${okved}.name`,
  type: 'string',
  title: 'Вид деятельности'
},

// Группы ликвидности
liquidityGroup: {
  sql: `${chartOfAccounts}.liquidity_group`,
  type: 'string',
  title: 'Группа ликвидности'
},

// ДДС категории
ddsCategory: {
  sql: `${ddsItems}.category_code`,
  type: 'string',
  title: 'Категория ДДС'
},

// Затраты
costType: {
  sql: `${costItems}.category_code`,
  type: 'string',
  title: 'Тип затрат (FIX/VAR)'
},

// РСБУ форма
rsbuForm: {
  sql: `${rsbuCodes}.form`,
  type: 'string',
  title: 'Форма отчетности'
}
```

### Примеры joins

```javascript
joins: {
  okved: {
    relationship: 'belongsTo',
    sql: `${Companies}.primary_okved = ${okved}.code`
  },
  
  rsbuMapping: {
    relationship: 'hasMany',
    sql: `${chartOfAccounts}.id = ${rsbuMapping}.account_id`
  }
}
```

---

## Полная схема таблиц

```
master.chart_of_accounts (416)
  ↓ FK: account_id
master.account_rsbu_mapping (105)
  ↓ FK: rsbu_code
master.rsbu_codes (177)

master.companies (23)
  ↓ FK: primary_okved
master.okved (2818)
  ↑ FK: okved_code
master.companies_okved

master.counterparties (1206)
  ↓ FK: primary_okved
master.okved
  ↑ FK: okved_code
master.counterparties_okved

master.dds_categories (7)
  ↓
master.dds_groups (31)
  ↓
master.dds_items (72)
  ↔
master.dds_items_mapping (73)

master.cost_categories (2)
  ↓
master.cost_groups (11)
  ↓
master.cost_items (167)
  ↔
master.cost_items_mapping (167)

master.periods (1)
```

---

## ETL Процессы

### Полная перезагрузка всех справочников

```bash
# 1. План счетов
python3 scripts/finance/etl/update_chart_of_accounts.py

# 2. ДДС
python3 scripts/finance/etl/load_dds_from_excel.py

# 3. Затраты
python3 scripts/finance/etl/load_cost_from_csv.py

# 4. ОКВЭД
python3 scripts/finance/etl/load_okved.py
python3 scripts/finance/etl/migrate_okved.py

# 5. РСБУ коды и маппинг
python3 scripts/finance/etl/load_rsbu_codes.py
psql -h localhost -U analytics_user -d analytics -f sql/rsbu_mapping.sql
```

### Комплексная загрузка

```bash
python3 scripts/finance/etl/load_master_references.py
```

---

## Представления (Views)

| Представление | Описание |
|---------------|----------|
| `v_okved_hierarchy` | Иерархия ОКВЭД с полными путями |
| `v_companies_with_okved` | Компании с расшифровкой ОКВЭД |
| `v_counterparties_with_okved` | Контрагенты с расшифровкой ОКВЭД |
| `v_account_rsbu_mapping` | Полный маппинг счетов на РСБУ |
| `v_accounts_without_rsbu` | Счета без маппинга на РСБУ |
| `v_rsbu_without_accounts` | Строки РСБУ без счетов |

---

## Статистика покрытия

| Справочник | Записей | Связей | Покрытие |
|------------|---------|--------|----------|
| План счетов | 416 | 105 → РСБУ | 25% |
| Компании | 23 | 23 → ОКВЭД | 100% |
| Контрагенты | 1206 | 0 → ОКВЭД | 0% |
| ДДС | 72 | 73 варианта | 101% |
| Затраты | 167 | 167 старых кодов | 100% |
| ОКВЭД | 2818 | — | — |
| РСБУ | 177 | 10 ← счета | 7% |

---

## Следующие шаги

### Приоритет 1: Завершение маппинга
- [ ] Завершить маппинг счетов → РСБУ (311 счетов)
- [ ] Обогатить контрагентов через DaData (1206 записей)

### Приоритет 2: Автоматизация
- [ ] Автоматическое формирование отчетных форм
- [ ] Валидация структуры отчетности
- [ ] Расчет итоговых строк

### Приоритет 3: Аналитика
- [ ] Cube.js модели для всех справочников
- [ ] Дашборды по отраслям (ОКВЭД)
- [ ] Анализ структуры затрат (FIX/VAR)
- [ ] Анализ ликвидности (A1-A4, P1-P4)

---

## Документация

- [OKVED_INTEGRATION.md](OKVED_INTEGRATION.md) — Подробное описание интеграции ОКВЭД
- [CUBE_ANALYTICS.md](CUBE_ANALYTICS.md) — Руководство по Cube.js
- [SERVER_DEPLOYMENT.md](SERVER_DEPLOYMENT.md) — Развертывание на сервере

---

**Версия:** 1.0  
**Дата:** 2025-11-24  
**База данных:** PostgreSQL 16, analytics.master schema  
**Коммит:** 5134e1f
