#!/usr/bin/env python3
"""
Загрузка справочника затрат из CSV файлов
Создание иерархии: категории → группы → статьи + маппинг старых кодов
"""

import pandas as pd
import psycopg2
from psycopg2.extras import execute_batch
import sys

DB_CONFIG = {
    'host': 'localhost',
    'port': 5432,
    'database': 'analytics',
    'user': 'analytics_user',
    'password': 'analytics_secure_2025'
}

BASE_PATH = '/opt/docagent/data/osv_revenue_0925/input/info_docs/Postgres/correct_2/master_schema_files'

def load_csv_files():
    """Загрузка данных из CSV"""
    print(f"📄 Чтение CSV файлов из {BASE_PATH}")
    
    categories = pd.read_csv(f'{BASE_PATH}/cost_categories.csv')
    groups = pd.read_csv(f'{BASE_PATH}/cost_groups.csv')
    items = pd.read_csv(f'{BASE_PATH}/cost_items.csv')
    
    # Фильтр активных
    items = items[items['is_active'] == True].copy()
    
    print(f"✅ Загружено:")
    print(f"   Категорий: {len(categories)}")
    print(f"   Групп: {len(groups)}")
    print(f"   Статей: {len(items)}")
    
    return categories, groups, items

def drop_old_tables(conn):
    """Удаление старых таблиц"""
    print("\n🗑️  Очистка старых таблиц затрат...")
    cursor = conn.cursor()
    
    try:
        cursor.execute("DROP TABLE IF EXISTS master.cost_items CASCADE")
        cursor.execute("DROP TABLE IF EXISTS master.cost_groups CASCADE")
        cursor.execute("DROP TABLE IF EXISTS master.cost_categories CASCADE")
        conn.commit()
        print("✅ Старые таблицы удалены")
    except Exception as e:
        conn.rollback()
        print(f"❌ Ошибка: {e}")
        raise

def create_schema(conn):
    """Создание схемы"""
    print("\n📐 Создание схемы...")
    cursor = conn.cursor()
    
    schema = """
    -- Категории затрат
    CREATE TABLE master.cost_categories (
        id SERIAL PRIMARY KEY,
        code VARCHAR(20) UNIQUE NOT NULL,
        name_ru VARCHAR(200) NOT NULL,
        name_en VARCHAR(200),
        sort_order INTEGER NOT NULL,
        is_active BOOLEAN DEFAULT TRUE,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    -- Группы затрат
    CREATE TABLE master.cost_groups (
        id SERIAL PRIMARY KEY,
        group_code VARCHAR(50) UNIQUE NOT NULL,
        name_ru VARCHAR(200) NOT NULL,
        name_en VARCHAR(200),
        category_id INTEGER NOT NULL REFERENCES master.cost_categories(id) ON DELETE RESTRICT,
        sort_order INTEGER,
        is_active BOOLEAN DEFAULT TRUE,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    -- Статьи затрат (нормализованные)
    CREATE TABLE master.cost_items (
        id SERIAL PRIMARY KEY,
        code VARCHAR(20) UNIQUE NOT NULL,
        name_ru VARCHAR(500) NOT NULL,
        name_en VARCHAR(500),
        category_id INTEGER NOT NULL REFERENCES master.cost_categories(id) ON DELETE RESTRICT,
        group_id INTEGER NOT NULL REFERENCES master.cost_groups(id) ON DELETE RESTRICT,
        sort_order INTEGER,
        is_active BOOLEAN DEFAULT TRUE,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    -- Маппинг старых кодов
    CREATE TABLE master.cost_items_mapping (
        id SERIAL PRIMARY KEY,
        cost_item_id INTEGER NOT NULL REFERENCES master.cost_items(id) ON DELETE CASCADE,
        old_code VARCHAR(200) NOT NULL,
        old_name VARCHAR(500),
        source_system VARCHAR(50) DEFAULT 'legacy',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(old_code, source_system)
    );

    -- Индексы
    CREATE INDEX idx_cost_items_code ON master.cost_items(code);
    CREATE INDEX idx_cost_items_category ON master.cost_items(category_id);
    CREATE INDEX idx_cost_items_group ON master.cost_items(group_id);
    CREATE INDEX idx_cost_groups_code ON master.cost_groups(group_code);
    CREATE INDEX idx_cost_groups_category ON master.cost_groups(category_id);
    CREATE INDEX idx_cost_mapping_item ON master.cost_items_mapping(cost_item_id);
    CREATE INDEX idx_cost_mapping_old_code ON master.cost_items_mapping(old_code);

    -- Комментарии
    COMMENT ON TABLE master.cost_categories IS 'Категории затрат (FIX/VAR - 2)';
    COMMENT ON TABLE master.cost_groups IS 'Группы затрат (11)';
    COMMENT ON TABLE master.cost_items IS 'Нормализованные статьи затрат (167)';
    COMMENT ON TABLE master.cost_items_mapping IS 'Маппинг старых кодов статей на нормализованные';
    """
    
    try:
        cursor.execute(schema)
        conn.commit()
        print("✅ Схема создана")
    except Exception as e:
        conn.rollback()
        print(f"❌ Ошибка: {e}")
        raise

def insert_categories(conn, df):
    """Вставка категорий"""
    print("\n📥 Загрузка категорий...")
    cursor = conn.cursor()
    
    category_ids = {}
    for _, row in df.iterrows():
        cursor.execute("""
            INSERT INTO master.cost_categories (code, name_ru, name_en, sort_order)
            VALUES (%s, %s, %s, %s)
            RETURNING id
        """, (row['code'], row['name_ru'], row.get('name_en'), row['sort_order']))
        
        category_ids[row['code']] = cursor.fetchone()[0]
    
    conn.commit()
    print(f"✅ Загружено категорий: {len(category_ids)}")
    return category_ids

def insert_groups(conn, df, category_ids):
    """Вставка групп"""
    print("\n📥 Загрузка групп...")
    cursor = conn.cursor()
    
    group_ids = {}
    for _, row in df.iterrows():
        category_id = category_ids.get(row['category_code'])
        if not category_id:
            print(f"⚠️  Пропуск группы {row['group_code']}: нет категории")
            continue
        
        cursor.execute("""
            INSERT INTO master.cost_groups (group_code, name_ru, category_id, sort_order)
            VALUES (%s, %s, %s, %s)
            RETURNING id
        """, (row['group_code'], row['name_ru'], category_id, row.get('sort_order')))
        
        group_id = cursor.fetchone()[0]
        group_ids[row['id']] = group_id  # Сохраняем по старому ID для связи
    
    conn.commit()
    print(f"✅ Загружено групп: {len(group_ids)}")
    return group_ids

def insert_items(conn, df, category_ids, group_ids):
    """Вставка статей и маппинга"""
    print("\n📥 Загрузка статей...")
    cursor = conn.cursor()
    
    item_ids = {}
    mapping_records = []
    
    for _, row in df.iterrows():
        code = row['new_code']
        name = row['cost_item_name']
        category_code = row['category_code']
        group_old_id = row['group_id']
        old_code = row.get('old_code')
        
        category_id = category_ids.get(category_code)
        group_id = group_ids.get(group_old_id)
        
        if not category_id or not group_id:
            print(f"⚠️  Пропуск статьи {code}: нет категории или группы")
            continue
        
        # Вставка статьи
        cursor.execute("""
            INSERT INTO master.cost_items (code, name_ru, category_id, group_id, sort_order)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id
        """, (code, name, category_id, group_id, row.get('id')))
        
        item_id = cursor.fetchone()[0]
        item_ids[code] = item_id
        
        # Подготовка маппинга
        if pd.notna(old_code) and old_code:
            # Извлечение старого названия из old_code (обычно в скобках)
            old_name = None
            if '(' in old_code:
                # Название может быть в формате "НАЗВАНИЕ_(ID)"
                parts = old_code.split('_(')
                if len(parts) > 1:
                    old_name = parts[0].replace('_', ' ')
            
            mapping_records.append((
                item_id,
                old_code,
                old_name,
                'legacy'
            ))
    
    conn.commit()
    print(f"✅ Загружено статей: {len(item_ids)}")
    
    # Вставка маппинга
    if mapping_records:
        print("\n📥 Создание маппинга старых кодов...")
        execute_batch(cursor, """
            INSERT INTO master.cost_items_mapping (cost_item_id, old_code, old_name, source_system)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (old_code, source_system) DO NOTHING
        """, mapping_records, page_size=100)
        
        conn.commit()
        print(f"✅ Создано маппингов: {len(mapping_records)}")
    
    return item_ids

def print_statistics(conn):
    """Статистика"""
    print("\n📊 СТАТИСТИКА")
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) FROM master.cost_categories")
    print(f"Категорий: {cursor.fetchone()[0]}")
    
    cursor.execute("SELECT COUNT(*) FROM master.cost_groups")
    print(f"Групп: {cursor.fetchone()[0]}")
    
    cursor.execute("SELECT COUNT(*) FROM master.cost_items")
    items_count = cursor.fetchone()[0]
    print(f"Статей: {items_count}")
    
    cursor.execute("SELECT COUNT(*) FROM master.cost_items_mapping")
    mapping_count = cursor.fetchone()[0]
    print(f"Маппингов старых кодов: {mapping_count}")
    
    cursor.execute("""
        SELECT c.name_ru, COUNT(i.id)
        FROM master.cost_categories c
        LEFT JOIN master.cost_items i ON c.id = i.category_id
        GROUP BY c.name_ru, c.sort_order
        ORDER BY c.sort_order
    """)
    print("\nРаспределение по категориям:")
    for cat, cnt in cursor.fetchall():
        print(f"  {cat}: {cnt}")
    
    # Группы постоянных затрат
    cursor.execute("""
        SELECT g.name_ru, COUNT(i.id)
        FROM master.cost_groups g
        LEFT JOIN master.cost_items i ON g.id = i.group_id
        WHERE g.group_code LIKE 'FIX%'
        GROUP BY g.name_ru, g.sort_order
        ORDER BY g.sort_order
    """)
    print("\nГруппы постоянных затрат:")
    for grp, cnt in cursor.fetchall():
        print(f"  {grp}: {cnt}")
    
    # Группы переменных затрат
    cursor.execute("""
        SELECT g.name_ru, COUNT(i.id)
        FROM master.cost_groups g
        LEFT JOIN master.cost_items i ON g.id = i.group_id
        WHERE g.group_code LIKE 'VAR%'
        GROUP BY g.name_ru, g.sort_order
        ORDER BY g.sort_order
    """)
    print("\nГруппы переменных затрат:")
    for grp, cnt in cursor.fetchall():
        print(f"  {grp}: {cnt}")

def main():
    print("=" * 70)
    print("🔄 ЗАГРУЗКА СПРАВОЧНИКА ЗАТРАТ")
    print("=" * 70)
    
    # Загрузка CSV
    categories_df, groups_df, items_df = load_csv_files()
    
    # Подключение
    print("\n🔌 Подключение к PostgreSQL...")
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        print("✅ Подключено")
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        sys.exit(1)
    
    try:
        # 1. Удаление старых таблиц
        drop_old_tables(conn)
        
        # 2. Создание схемы
        create_schema(conn)
        
        # 3. Загрузка данных
        category_ids = insert_categories(conn, categories_df)
        group_ids = insert_groups(conn, groups_df, category_ids)
        insert_items(conn, items_df, category_ids, group_ids)
        
        # 4. Статистика
        print_statistics(conn)
        
        print("\n" + "=" * 70)
        print("✅ ЗАГРУЗКА ЗАВЕРШЕНА УСПЕШНО")
        print("=" * 70)
        
    except Exception as e:
        print(f"\n❌ ОШИБКА: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        conn.close()

if __name__ == '__main__':
    main()
