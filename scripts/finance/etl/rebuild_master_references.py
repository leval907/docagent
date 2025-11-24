#!/usr/bin/env python3
"""
Пересоздание справочников master с правильной иерархической структурой
- ДДС: категории → группы → статьи
- Затраты: категории → группы → статьи
"""

import pandas as pd
import psycopg2
from psycopg2.extras import execute_batch
import sys
from pathlib import Path

DB_CONFIG = {
    'host': 'localhost',
    'port': 5432,
    'database': 'analytics',
    'user': 'analytics_user',
    'password': 'analytics_secure_2025'
}

BASE_PATH = '/tmp/master_refs'

def drop_old_tables(conn):
    """Удаление старых таблиц ДДС и затрат"""
    print("\n🗑️  Удаление старых таблиц...")
    cursor = conn.cursor()
    
    try:
        # Удаляем старые таблицы
        cursor.execute("DROP TABLE IF EXISTS master.dds_items CASCADE")
        cursor.execute("DROP TABLE IF EXISTS master.cost_items CASCADE")
        conn.commit()
        print("✅ Старые таблицы удалены")
    except Exception as e:
        conn.rollback()
        print(f"❌ Ошибка удаления: {e}")
        raise

def create_dds_schema(conn):
    """Создание схемы справочника ДДС"""
    print("\n📐 Создание схемы ДДС...")
    cursor = conn.cursor()
    
    schema_sql = """
    -- Категории ДДС
    CREATE TABLE IF NOT EXISTS master.dds_categories (
        id SERIAL PRIMARY KEY,
        code VARCHAR(20) UNIQUE NOT NULL,
        name_ru VARCHAR(200) NOT NULL,
        name_en VARCHAR(200),
        activity_type VARCHAR(50) NOT NULL,
        direction VARCHAR(20) NOT NULL,
        sort_order INTEGER NOT NULL,
        color_hex VARCHAR(7),
        ifrs_mapping VARCHAR(100),
        is_active BOOLEAN DEFAULT TRUE NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL
    );

    -- Группы ДДС
    CREATE TABLE IF NOT EXISTS master.dds_groups (
        id SERIAL PRIMARY KEY,
        name_ru VARCHAR(200) NOT NULL,
        name_en VARCHAR(200),
        category_id INTEGER NOT NULL REFERENCES master.dds_categories(id) ON DELETE RESTRICT,
        description TEXT,
        sort_order INTEGER,
        is_active BOOLEAN DEFAULT TRUE NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL
    );

    -- Статьи ДДС
    CREATE TABLE IF NOT EXISTS master.dds_items (
        id SERIAL PRIMARY KEY,
        code VARCHAR(20) UNIQUE NOT NULL,
        name_ru VARCHAR(500) NOT NULL,
        name_en VARCHAR(500),
        category_id INTEGER NOT NULL REFERENCES master.dds_categories(id) ON DELETE RESTRICT,
        group_id INTEGER NOT NULL REFERENCES master.dds_groups(id) ON DELETE RESTRICT,
        description TEXT,
        sort_order INTEGER,
        is_active BOOLEAN DEFAULT TRUE NOT NULL,
        account_mapping VARCHAR(100),
        comments TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL
    );

    -- Индексы
    CREATE INDEX IF NOT EXISTS idx_dds_items_code ON master.dds_items(code);
    CREATE INDEX IF NOT EXISTS idx_dds_items_category ON master.dds_items(category_id);
    CREATE INDEX IF NOT EXISTS idx_dds_items_group ON master.dds_items(group_id);
    CREATE INDEX IF NOT EXISTS idx_dds_groups_category ON master.dds_groups(category_id);
    """
    
    try:
        cursor.execute(schema_sql)
        conn.commit()
        print("✅ Схема ДДС создана")
    except Exception as e:
        conn.rollback()
        print(f"❌ Ошибка создания схемы ДДС: {e}")
        raise

def create_cost_schema(conn):
    """Создание схемы справочника затрат"""
    print("\n📐 Создание схемы затрат...")
    cursor = conn.cursor()
    
    schema_sql = """
    -- Категории затрат
    CREATE TABLE IF NOT EXISTS master.cost_categories (
        id SERIAL PRIMARY KEY,
        code VARCHAR(20) UNIQUE NOT NULL,
        name_ru VARCHAR(200) NOT NULL,
        name_en VARCHAR(200),
        sort_order INTEGER NOT NULL,
        is_active BOOLEAN DEFAULT TRUE NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL
    );

    -- Группы затрат
    CREATE TABLE IF NOT EXISTS master.cost_groups (
        id SERIAL PRIMARY KEY,
        name_ru VARCHAR(200) NOT NULL,
        name_en VARCHAR(200),
        category_id INTEGER NOT NULL REFERENCES master.cost_categories(id) ON DELETE RESTRICT,
        description TEXT,
        sort_order INTEGER,
        is_active BOOLEAN DEFAULT TRUE NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL
    );

    -- Статьи затрат
    CREATE TABLE IF NOT EXISTS master.cost_items (
        id SERIAL PRIMARY KEY,
        code VARCHAR(20) UNIQUE NOT NULL,
        name_ru VARCHAR(500) NOT NULL,
        name_en VARCHAR(500),
        category_id INTEGER NOT NULL REFERENCES master.cost_categories(id) ON DELETE RESTRICT,
        group_id INTEGER NOT NULL REFERENCES master.cost_groups(id) ON DELETE RESTRICT,
        description TEXT,
        sort_order INTEGER,
        is_active BOOLEAN DEFAULT TRUE NOT NULL,
        account_mapping VARCHAR(100),
        comments TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL
    );

    -- Индексы
    CREATE INDEX IF NOT EXISTS idx_cost_items_code ON master.cost_items(code);
    CREATE INDEX IF NOT EXISTS idx_cost_items_category ON master.cost_items(category_id);
    CREATE INDEX IF NOT EXISTS idx_cost_items_group ON master.cost_items(group_id);
    CREATE INDEX IF NOT EXISTS idx_cost_groups_category ON master.cost_groups(category_id);
    """
    
    try:
        cursor.execute(schema_sql)
        conn.commit()
        print("✅ Схема затрат создана")
    except Exception as e:
        conn.rollback()
        print(f"❌ Ошибка создания схемы затрат: {e}")
        raise

def load_dds_data(conn):
    """Загрузка данных ДДС"""
    print("\n📥 Загрузка данных ДДС...")
    cursor = conn.cursor()
    
    # 1. Категории
    categories_df = pd.read_csv(f'{BASE_PATH}/import_1_categories.csv')
    print(f"   Категорий: {len(categories_df)}")
    
    for _, row in categories_df.iterrows():
        cursor.execute("""
            INSERT INTO master.dds_categories (code, name_ru, name_en, activity_type, direction, sort_order, color_hex, ifrs_mapping)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (
            row['code'], row['name_ru'], row.get('name_en'), 
            row['activity_type'], row['direction'], row['sort_order'],
            row.get('color_hex'), row.get('ifrs_mapping')
        ))
    conn.commit()
    
    # 2. Группы
    groups_df = pd.read_csv(f'{BASE_PATH}/import_2_groups.csv')
    print(f"   Групп: {len(groups_df)}")
    
    for _, row in groups_df.iterrows():
        # Найти category_id по коду
        cursor.execute("SELECT id FROM master.dds_categories WHERE code = %s", (row['category_code'],))
        category_id = cursor.fetchone()[0]
        
        cursor.execute("""
            INSERT INTO master.dds_groups (name_ru, name_en, category_id, sort_order)
            VALUES (%s, %s, %s, %s)
            RETURNING id
        """, (row['name_ru'], row.get('name_en'), category_id, row.get('sort_order')))
    conn.commit()
    
    # 3. Статьи
    items_df = pd.read_csv(f'{BASE_PATH}/import_3_items.csv')
    print(f"   Статей: {len(items_df)}")
    
    for _, row in items_df.iterrows():
        # Найти category_id и group_id
        cursor.execute("SELECT id FROM master.dds_categories WHERE code = %s", (row['category_code'],))
        category_id = cursor.fetchone()[0]
        
        cursor.execute("""
            SELECT id FROM master.dds_groups 
            WHERE name_ru = %s AND category_id = %s
        """, (row['group_name_ru'], category_id))
        group_id = cursor.fetchone()[0]
        
        cursor.execute("""
            INSERT INTO master.dds_items (code, name_ru, name_en, category_id, group_id, sort_order, account_mapping)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (
            row['code'], row['name_ru'], row.get('name_en'), 
            category_id, group_id, row.get('sort_order'), row.get('account_mapping')
        ))
    conn.commit()
    
    print("✅ Данные ДДС загружены")

def load_cost_data(conn):
    """Загрузка данных затрат"""
    print("\n📥 Загрузка данных затрат...")
    cursor = conn.cursor()
    
    # 1. Категории
    categories_df = pd.read_csv(f'{BASE_PATH}/cost_categories.csv')
    print(f"   Категорий: {len(categories_df)}")
    
    for _, row in categories_df.iterrows():
        cursor.execute("""
            INSERT INTO master.cost_categories (code, name_ru, name_en, sort_order)
            VALUES (%s, %s, %s, %s)
            RETURNING id
        """, (row['code'], row['name_ru'], row.get('name_en'), row['sort_order']))
    conn.commit()
    
    # 2. Группы
    groups_df = pd.read_csv(f'{BASE_PATH}/cost_groups.csv')
    print(f"   Групп: {len(groups_df)}")
    
    for _, row in groups_df.iterrows():
        cursor.execute("SELECT id FROM master.cost_categories WHERE code = %s", (row['category_code'],))
        category_id = cursor.fetchone()[0]
        
        cursor.execute("""
            INSERT INTO master.cost_groups (name_ru, name_en, category_id, sort_order)
            VALUES (%s, %s, %s, %s)
            RETURNING id
        """, (row['name_ru'], row.get('name_en'), category_id, row.get('sort_order')))
    conn.commit()
    
    # 3. Статьи
    items_df = pd.read_csv(f'{BASE_PATH}/cost_items.csv')
    print(f"   Статей: {len(items_df)}")
    
    for _, row in items_df.iterrows():
        cursor.execute("SELECT id FROM master.cost_categories WHERE code = %s", (row['category_code'],))
        category_id = cursor.fetchone()[0]
        
        cursor.execute("""
            SELECT id FROM master.cost_groups 
            WHERE name_ru = %s AND category_id = %s
        """, (row['group_name_ru'], category_id))
        group_id = cursor.fetchone()[0]
        
        cursor.execute("""
            INSERT INTO master.cost_items (code, name_ru, name_en, category_id, group_id, sort_order, account_mapping)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (
            row['code'], row['name_ru'], row.get('name_en'), 
            category_id, group_id, row.get('sort_order'), row.get('account_mapping')
        ))
    conn.commit()
    
    print("✅ Данные затрат загружены")

def print_statistics(conn):
    """Вывод статистики"""
    print("\n📊 СТАТИСТИКА")
    cursor = conn.cursor()
    
    print("\n=== ДДС ===")
    cursor.execute("SELECT COUNT(*) FROM master.dds_categories")
    print(f"Категорий: {cursor.fetchone()[0]}")
    
    cursor.execute("SELECT COUNT(*) FROM master.dds_groups")
    print(f"Групп: {cursor.fetchone()[0]}")
    
    cursor.execute("SELECT COUNT(*) FROM master.dds_items")
    print(f"Статей: {cursor.fetchone()[0]}")
    
    cursor.execute("""
        SELECT c.name_ru, COUNT(i.id)
        FROM master.dds_categories c
        LEFT JOIN master.dds_items i ON c.id = i.category_id
        GROUP BY c.name_ru
        ORDER BY c.sort_order
    """)
    print("\nПо категориям:")
    for cat, cnt in cursor.fetchall():
        print(f"  {cat}: {cnt}")
    
    print("\n=== ЗАТРАТЫ ===")
    cursor.execute("SELECT COUNT(*) FROM master.cost_categories")
    print(f"Категорий: {cursor.fetchone()[0]}")
    
    cursor.execute("SELECT COUNT(*) FROM master.cost_groups")
    print(f"Групп: {cursor.fetchone()[0]}")
    
    cursor.execute("SELECT COUNT(*) FROM master.cost_items")
    print(f"Статей: {cursor.fetchone()[0]}")
    
    cursor.execute("""
        SELECT c.name_ru, COUNT(i.id)
        FROM master.cost_categories c
        LEFT JOIN master.cost_items i ON c.id = i.category_id
        GROUP BY c.name_ru
        ORDER BY c.sort_order
    """)
    print("\nПо категориям:")
    for cat, cnt in cursor.fetchall():
        print(f"  {cat}: {cnt}")

def main():
    print("=" * 70)
    print("🔄 ПЕРЕСОЗДАНИЕ СПРАВОЧНИКОВ MASTER (ДДС + ЗАТРАТЫ)")
    print("=" * 70)
    
    # Проверка файлов
    required_files = [
        'import_1_categories.csv', 'import_2_groups.csv', 'import_3_items.csv',
        'cost_categories.csv', 'cost_groups.csv', 'cost_items.csv'
    ]
    
    for file in required_files:
        if not Path(f'{BASE_PATH}/{file}').exists():
            print(f"❌ Файл не найден: {file}")
            sys.exit(1)
    
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
        
        # 2. Создание схем
        create_dds_schema(conn)
        create_cost_schema(conn)
        
        # 3. Загрузка данных
        load_dds_data(conn)
        load_cost_data(conn)
        
        # 4. Статистика
        print_statistics(conn)
        
        print("\n" + "=" * 70)
        print("✅ ПЕРЕСОЗДАНИЕ ЗАВЕРШЕНО УСПЕШНО")
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
