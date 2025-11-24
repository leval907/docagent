# Интеграция справочника ОКВЭД 2

## Обзор

Справочник ОКВЭД 2 (Общероссийский классификатор видов экономической деятельности) интегрирован в схему `master` для классификации компаний группы и контрагентов по видам деятельности.

### Структура данных

**Загружено:** 2818 кодов ОКВЭД  
**Источник:** okved_2.xls (версия от февраля 2022)  
**Уровней иерархии:** 6

```
Раздел (буква)      → 21 кода    (A, B, C...)
Класс (XX)          → 88 кодов   (01, 62, 95...)
Подкласс (XX.X)     → 272 кода   (01.1, 62.0...)
Группа (XX.XX)      → 623 кода   (01.11, 62.01...)
Подгруппа (XX.XX.X) → 1190 кодов (01.11.1...)
Вид (XX.XX.XX)      → 624 кода   (01.11.11...)
```

## Таблицы базы данных

### 1. master.okved
Полный справочник ОКВЭД с иерархией:

```sql
CREATE TABLE master.okved (
    id SERIAL PRIMARY KEY,
    code VARCHAR(20) UNIQUE NOT NULL,      -- Уникальный код (J, 62, 62.01...)
    parent_code VARCHAR(20),                -- Ссылка на родительский код
    section VARCHAR(1),                     -- Раздел (A-U)
    name VARCHAR(1000) NOT NULL,            -- Название вида деятельности
    comment TEXT,                           -- Дополнительное описание
    level INTEGER NOT NULL,                 -- Уровень иерархии (1-6)
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### 2. master.companies_okved
Связь компаний с множественными кодами ОКВЭД:

```sql
CREATE TABLE master.companies_okved (
    id SERIAL PRIMARY KEY,
    company_id INTEGER NOT NULL REFERENCES master.companies(id),
    okved_code VARCHAR(20) NOT NULL,
    okved_id INTEGER REFERENCES master.okved(id),
    is_primary BOOLEAN DEFAULT FALSE,       -- Основной вид деятельности
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(company_id, okved_code)
);
```

### 3. master.counterparties_okved
Связь контрагентов с кодами ОКВЭД:

```sql
CREATE TABLE master.counterparties_okved (
    id SERIAL PRIMARY KEY,
    counterparty_id INTEGER NOT NULL REFERENCES master.counterparties(id),
    okved_code VARCHAR(20) NOT NULL,
    okved_id INTEGER REFERENCES master.okved(id),
    is_primary BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(counterparty_id, okved_code)
);
```

### 4. Расширение существующих таблиц
Добавлены колонки `primary_okved`:

```sql
ALTER TABLE master.companies 
ADD COLUMN primary_okved VARCHAR(20);

ALTER TABLE master.counterparties 
ADD COLUMN primary_okved VARCHAR(20);
```

## Представления (Views)

### master.v_okved_hierarchy
Рекурсивное представление с полными путями иерархии:

```sql
SELECT * FROM master.v_okved_hierarchy WHERE code = '62.01';
```

**Результат:**
```
code   | level | name                              | path_codes
-------|-------|-----------------------------------|------------------
62.01  | 4     | Разработка ПО                     | J → 62 → 62.0 → 62.01
```

**Колонки:**
- `id`, `code`, `parent_code`, `section`, `name`, `comment`, `level`
- `path_codes` — полный путь кодов (J → 62 → 62.0 → 62.01)
- `path_names` — полный путь названий
- `depth` — глубина в иерархии
- `root_section` — корневой раздел
- `class_code` — класс (2-й уровень)

### master.v_companies_with_okved
Компании с расшифровкой всех ОКВЭД:

```sql
SELECT * FROM master.v_companies_with_okved WHERE company_name LIKE 'ДЖУЛ%';
```

**Колонки:**
- `company_id`, `company_name`, `inn`
- `primary_okved` — основной код
- `primary_okved_name` — расшифровка
- `primary_section` — раздел (J, C, M...)
- `primary_path` — полная иерархия
- `additional_okved_codes[]` — массив дополнительных кодов
- `additional_okved_names[]` — массив расшифровок

### master.v_counterparties_with_okved
Аналогичное представление для контрагентов.

## Примеры использования

### 1. Найти все компании в IT-секторе

```sql
SELECT 
    company_name,
    inn,
    primary_okved,
    primary_okved_name
FROM master.v_companies_with_okved
WHERE primary_section = 'J';
```

**Результат:**
```
ДЖУЛ ЛАЙФ ООО         | 5024248306 | 62.01 | Разработка ПО
ГЛОБАЛКОНСАЛТ ООО     | 7722765650 | 73.20 | Исследование конъюнктуры
```

### 2. Распределение компаний по разделам ОКВЭД

```sql
SELECT 
    o.section,
    o_section.name AS section_name,
    COUNT(*) AS companies_count
FROM master.companies c
INNER JOIN master.okved o ON c.primary_okved = o.code
LEFT JOIN master.okved o_section 
    ON o.section = o_section.code AND o_section.level = 1
WHERE c.primary_okved IS NOT NULL
GROUP BY o.section, o_section.name
ORDER BY companies_count DESC;
```

**Результат (топ-3):**
```
section | section_name                              | companies_count
--------|-------------------------------------------|----------------
L       | Операции с недвижимостью                  | 11
M       | Деятельность профессиональная             | 6
J       | Информация и связь                        | 2
```

### 3. Поиск компаний по виду деятельности

```sql
-- Все компании в строительстве (раздел F)
SELECT company_name, primary_okved, primary_okved_name
FROM master.v_companies_with_okved
WHERE primary_okved LIKE 'F%' OR primary_section = 'F';

-- Все компании с кодом "управление недвижимостью"
SELECT company_name, primary_okved, primary_okved_name
FROM master.v_companies_with_okved
WHERE primary_okved LIKE '68.%';
```

### 4. Полная иерархия конкретного кода

```sql
SELECT code, level, name, path_codes
FROM master.v_okved_hierarchy
WHERE code = '62.01';
```

### 5. Все подкоды раздела

```sql
-- Все коды раздела J (информация и связь)
SELECT code, name, level
FROM master.okved
WHERE section = 'J'
ORDER BY code;
```

### 6. Добавление дополнительных ОКВЭД для компании

```sql
-- Добавить дополнительный вид деятельности
INSERT INTO master.companies_okved (company_id, okved_code, okved_id, is_primary)
SELECT 
    c.id,
    '62.02',
    o.id,
    FALSE
FROM master.companies c
CROSS JOIN master.okved o
WHERE c.inn = '5024248306'  -- ДЖУЛ ЛАЙФ
AND o.code = '62.02';       -- Консультирование в области IT
```

## Статистика (текущее состояние)

### Компании группы
- **Всего:** 23 компании
- **С ОКВЭД:** 23 (100%)
- **Основные виды деятельности:**
  - 68.20 (Аренда недвижимости): 6 компаний
  - 68.32 (Управление недвижимостью): 3 компании
  - 71.12 (Инженерные изыскания): 5 компаний
  - 62.01 (Разработка ПО): 2 компании

### Разделы ОКВЭД компаний
1. **L** (Недвижимость): 11 компаний (48%)
2. **M** (Профессиональная деятельность): 6 компаний (26%)
3. **J** (Информация и связь): 2 компании (9%)
4. **F** (Строительство): 2 компании (9%)
5. **N, Q** (Прочие): 2 компании (8%)

### Контрагенты
- **Всего:** 1206 контрагентов
- **С ОКВЭД:** 0 (требуется enrichment через DaData)

## ETL процессы

### Загрузка справочника ОКВЭД
```bash
python3 scripts/finance/etl/load_okved.py
```

**Что делает:**
1. Читает okved_2.xls из /tmp/okved/
2. Создает таблицы (okved, companies_okved, counterparties_okved)
3. Загружает 2818 кодов с иерархией
4. Создает индексы для быстрого поиска
5. Добавляет колонки primary_okved в companies/counterparties

### Миграция существующих данных
```bash
python3 scripts/finance/etl/migrate_okved.py
```

**Что делает:**
1. Копирует данные из companies.okved → companies.primary_okved
2. Проверяет наличие ОКВЭД у контрагентов
3. Показывает статистику покрытия
4. Анализирует распределение по разделам

## Интеграция с Cube.js

### Dimensions для фильтрации

```javascript
// cube.js
cube('Companies', {
  dimensions: {
    okvedSection: {
      sql: `${okved}.section`,
      type: 'string',
      title: 'Раздел ОКВЭД'
    },
    
    okvedCode: {
      sql: `primary_okved`,
      type: 'string',
      title: 'Код ОКВЭД'
    },
    
    okvedName: {
      sql: `${okved}.name`,
      type: 'string',
      title: 'Вид деятельности'
    },
    
    industryGroup: {
      sql: `
        CASE 
          WHEN ${okved}.section = 'J' THEN 'IT и связь'
          WHEN ${okved}.section IN ('L', 'F') THEN 'Недвижимость и строительство'
          WHEN ${okved}.section = 'M' THEN 'Профессиональные услуги'
          ELSE 'Прочие'
        END
      `,
      type: 'string',
      title: 'Отраслевая группа'
    }
  },
  
  joins: {
    okved: {
      relationship: 'belongsTo',
      sql: `${Companies}.primary_okved = ${okved}.code`
    }
  }
});
```

### Примеры запросов

```javascript
// Выручка по разделам ОКВЭД
{
  measures: ['OsvRevenue.totalRevenue'],
  dimensions: ['Companies.okvedSection', 'Companies.okvedName'],
  order: { 'OsvRevenue.totalRevenue': 'desc' }
}

// Компании по отраслям
{
  measures: ['Companies.count'],
  dimensions: ['Companies.industryGroup'],
  order: { 'Companies.count': 'desc' }
}
```

## Обогащение данных через DaData

### Для контрагентов

```python
# Пример обогащения ОКВЭД через DaData API
import requests

def enrich_counterparty_okved(inn: str):
    url = "https://suggestions.dadata.ru/suggestions/api/4_1/rs/findById/party"
    headers = {
        "Authorization": f"Token {DADATA_API_KEY}",
        "Content-Type": "application/json"
    }
    data = {"query": inn}
    
    response = requests.post(url, json=data, headers=headers)
    result = response.json()
    
    if result.get('suggestions'):
        company = result['suggestions'][0]['data']
        primary_okved = company.get('okved')
        additional_okved = company.get('okveds', [])
        
        # Обновление в БД
        cursor.execute("""
            UPDATE master.counterparties
            SET primary_okved = %s
            WHERE inn = %s
        """, (primary_okved, inn))
        
        # Добавление дополнительных ОКВЭД
        for okved in additional_okved:
            cursor.execute("""
                INSERT INTO master.counterparties_okved 
                (counterparty_id, okved_code, is_primary)
                SELECT id, %s, FALSE
                FROM master.counterparties
                WHERE inn = %s
                ON CONFLICT (counterparty_id, okved_code) DO NOTHING
            """, (okved['code'], inn))
```

## Следующие шаги

1. ✅ Справочник ОКВЭД загружен (2818 кодов)
2. ✅ Все компании группы имеют ОКВЭД (23/23)
3. ⏳ Обогатить контрагентов через DaData (0/1206)
4. ⏳ Создать Cube.js модели с ОКВЭД dimensions
5. ⏳ Добавить аналитику по отраслям в дашборды

## Полезные запросы

### Проверка корректности иерархии
```sql
-- Найти коды без родителя (кроме разделов)
SELECT code, name, level, parent_code
FROM master.okved
WHERE level > 1 
AND (parent_code IS NULL OR parent_code = '')
ORDER BY code;

-- Найти несуществующих родителей
SELECT o1.code, o1.parent_code, o1.name
FROM master.okved o1
LEFT JOIN master.okved o2 ON o1.parent_code = o2.code
WHERE o1.parent_code IS NOT NULL 
AND o1.parent_code != ''
AND o2.code IS NULL;
```

### Топ ОКВЭД среди контрагентов (после enrichment)
```sql
SELECT 
    cp.primary_okved,
    o.name,
    COUNT(*) AS counterparty_count
FROM master.counterparties cp
INNER JOIN master.okved o ON cp.primary_okved = o.code
WHERE cp.primary_okved IS NOT NULL
GROUP BY cp.primary_okved, o.name
ORDER BY counterparty_count DESC
LIMIT 20;
```

### Сравнение отраслевой структуры компаний vs контрагентов
```sql
SELECT 
    'Companies' AS entity_type,
    o.section,
    o_section.name AS section_name,
    COUNT(*) AS count
FROM master.companies c
INNER JOIN master.okved o ON c.primary_okved = o.code
LEFT JOIN master.okved o_section ON o.section = o_section.code AND o_section.level = 1
GROUP BY o.section, o_section.name

UNION ALL

SELECT 
    'Counterparties' AS entity_type,
    o.section,
    o_section.name AS section_name,
    COUNT(*) AS count
FROM master.counterparties cp
INNER JOIN master.okved o ON cp.primary_okved = o.code
LEFT JOIN master.okved o_section ON o.section = o_section.code AND o_section.level = 1
GROUP BY o.section, o_section.name

ORDER BY entity_type, count DESC;
```

---

**Дата создания:** 2025  
**Источник:** ОКВЭД 2 (версия от 02.2022)  
**Скрипты:** `scripts/finance/etl/load_okved.py`, `scripts/finance/etl/migrate_okved.py`  
**SQL:** `sql/okved_views.sql`
