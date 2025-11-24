#!/usr/bin/env python3
"""
Загрузка справочника ДДС из выверенного файла dds_final_v3_corrected.xlsx
Создание иерархии: категории → группы → статьи
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

EXCEL_FILE = '/opt/docagent/data/osv_revenue_0925/input/info_docs/Postgres/correct_2/dds_final_v3_corrected.xlsx'

# Маппинг категорий на код
CATEGORY_MAPPING = {
    'Операционная деятельность - Поступления': 'OPS_IN',
    'Операционная деятельность - Платежи': 'OPS_OUT',
    'Инвестиционная деятельность - Поступления': 'INV_IN',
    'Инвестиционная деятельность - Платежи': 'INV_OUT',
    'Финансовая деятельность - Поступления': 'FIN_IN',
    'Финансовая деятельность - Платежи': 'FIN_OUT',
    'Внутренние переводы': 'TRF'
}

# Маппинг вида деятельности
ACTIVITY_MAPPING = {
    'Операционная деятельность - Поступления': 'OPERATING',
    'Операционная деятельность - Платежи': 'OPERATING',
    'Инвестиционная деятельность - Поступления': 'INVESTING',
    'Инвестиционная деятельность - Платежи': 'INVESTING',
    'Финансовая деятельность - Поступления': 'FINANCING',
    'Финансовая деятельность - Платежи': 'FINANCING',
    'Внутренние переводы': 'TRANSFER'
}

def load_excel():
    """Загрузка данных из Excel"""
    print(f"📄 Чтение: {EXCEL_FILE}")
    df = pd.read_excel(EXCEL_FILE, sheet_name='Справочник ДДС')
    
    # Фильтр активных
    df = df[df['Активно'] == 'Да'].copy()
    
    print(f"✅ Загружено {len(df)} записей (включая варианты названий)")
    
    # Статистика по дубликатам кодов
    duplicates = df[df.duplicated(subset=['Новый код'], keep=False)]
    if len(duplicates) > 0:
        unique_codes = duplicates['Новый код'].nunique()
        print(f"ℹ️  Найдено {unique_codes} кодов с вариантами названий ({len(duplicates)} записей)")
    
    return df

def drop_old_tables(conn):
    """Удаление старых таблиц"""
    print("\n🗑️  Очистка старых таблиц ДДС...")
    cursor = conn.cursor()
    
    try:
        cursor.execute("DROP TABLE IF EXISTS master.dds_items CASCADE")
        cursor.execute("DROP TABLE IF EXISTS master.dds_groups CASCADE")
        cursor.execute("DROP TABLE IF EXISTS master.dds_categories CASCADE")
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
    -- Категории ДДС
    CREATE TABLE master.dds_categories (
        id SERIAL PRIMARY KEY,
        code VARCHAR(20) UNIQUE NOT NULL,
        name_ru VARCHAR(200) NOT NULL,
        activity_type VARCHAR(50) NOT NULL,
        direction VARCHAR(20) NOT NULL,
        sort_order INTEGER NOT NULL,
        is_active BOOLEAN DEFAULT TRUE,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    -- Группы ДДС
    CREATE TABLE master.dds_groups (
        id SERIAL PRIMARY KEY,
        name_ru VARCHAR(200) NOT NULL,
        category_id INTEGER NOT NULL REFERENCES master.dds_categories(id) ON DELETE RESTRICT,
        sort_order INTEGER,
        is_active BOOLEAN DEFAULT TRUE,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(name_ru, category_id)
    );

    -- Статьи ДДС (нормализованные)
    CREATE TABLE master.dds_items (
        id SERIAL PRIMARY KEY,
        code VARCHAR(20) UNIQUE NOT NULL,
        name_ru VARCHAR(500) NOT NULL,
        category_id INTEGER NOT NULL REFERENCES master.dds_categories(id) ON DELETE RESTRICT,
        group_id INTEGER NOT NULL REFERENCES master.dds_groups(id) ON DELETE RESTRICT,
        sort_order INTEGER,
        is_active BOOLEAN DEFAULT TRUE,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    -- Маппинг старых названий на нормализованные статьи
    CREATE TABLE master.dds_items_mapping (
        id SERIAL PRIMARY KEY,
        dds_item_id INTEGER NOT NULL REFERENCES master.dds_items(id) ON DELETE CASCADE,
        old_name VARCHAR(500) NOT NULL,
        old_id INTEGER,
        source_system VARCHAR(50) DEFAULT 'legacy',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(old_name, source_system)
    );

    -- Индексы
    CREATE INDEX idx_dds_items_code ON master.dds_items(code);
    CREATE INDEX idx_dds_items_category ON master.dds_items(category_id);
    CREATE INDEX idx_dds_items_group ON master.dds_items(group_id);
    CREATE INDEX idx_dds_groups_category ON master.dds_groups(category_id);
    CREATE INDEX idx_dds_mapping_item ON master.dds_items_mapping(dds_item_id);
    CREATE INDEX idx_dds_mapping_old_name ON master.dds_items_mapping(old_name);

    -- Комментарии
    COMMENT ON TABLE master.dds_categories IS 'Категории движения денежных средств (7)';
    COMMENT ON TABLE master.dds_groups IS 'Группы статей ДДС (~30)';
    COMMENT ON TABLE master.dds_items IS 'Нормализованные статьи ДДС (уникальные коды)';
    COMMENT ON TABLE master.dds_items_mapping IS 'Маппинг старых названий статей на нормализованные';
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
    
    # Получить уникальные категории
    categories = df['Вид деятельности'].unique()
    
    category_ids = {}
    for idx, category_name in enumerate(sorted(categories), 1):
        code = CATEGORY_MAPPING.get(category_name)
        if not code:
            print(f"⚠️  Неизвестная категория: {category_name}")
            continue
        
        activity_type = ACTIVITY_MAPPING.get(category_name)
        direction = 'inflow' if 'Поступления' in category_name else ('outflow' if 'Платежи' in category_name else 'transfer')
        
        cursor.execute("""
            INSERT INTO master.dds_categories (code, name_ru, activity_type, direction, sort_order)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id
        """, (code, category_name, activity_type, direction, idx))
        
        category_ids[category_name] = cursor.fetchone()[0]
    
    conn.commit()
    print(f"✅ Загружено категорий: {len(category_ids)}")
    return category_ids

def insert_groups(conn, df, category_ids):
    """Вставка групп"""
    print("\n📥 Загрузка групп...")
    cursor = conn.cursor()
    
    # Получить уникальные пары (категория, группа)
    groups = df[['Вид деятельности', 'Группа статьи']].drop_duplicates()
    
    group_ids = {}
    for idx, (_, row) in enumerate(groups.iterrows(), 1):
        category_name = row['Вид деятельности']
        group_name = row['Группа статьи']
        
        if pd.isna(group_name) or group_name == '':
            group_name = 'Без группы'
        
        category_id = category_ids.get(category_name)
        if not category_id:
            continue
        
        cursor.execute("""
            INSERT INTO master.dds_groups (name_ru, category_id, sort_order)
            VALUES (%s, %s, %s)
            ON CONFLICT (name_ru, category_id) DO NOTHING
            RETURNING id
        """, (group_name, category_id, idx))
        
        result = cursor.fetchone()
        if result:
            group_ids[(category_name, group_name)] = result[0]
        else:
            # Если уже существует, получить id
            cursor.execute("""
                SELECT id FROM master.dds_groups 
                WHERE name_ru = %s AND category_id = %s
            """, (group_name, category_id))
            group_ids[(category_name, group_name)] = cursor.fetchone()[0]
    
    conn.commit()
    print(f"✅ Загружено групп: {len(group_ids)}")
    return group_ids

def insert_items(conn, df, category_ids, group_ids):
    """Вставка нормализованных статей и маппинга"""
    print("\n📥 Загрузка статей...")
    cursor = conn.cursor()
    
    # Группировка по коду (нормализованная статья)
    unique_items = df.groupby('Новый код').first().reset_index()
    
    print(f"   Уникальных статей: {len(unique_items)}")
    
    # Словарь для хранения id нормализованных статей
    item_ids = {}
    
    # Вставка уникальных статей
    for idx, row in unique_items.iterrows():
        code = row['Новый код']
        name = row['Название статьи']
        category_name = row['Вид деятельности']
        group_name = row['Группа статьи']
        
        if pd.isna(group_name) or group_name == '':
            group_name = 'Без группы'
        
        category_id = category_ids.get(category_name)
        group_id = group_ids.get((category_name, group_name))
        
        if not category_id or not group_id:
            print(f"⚠️  Пропуск статьи {code}: нет категории или группы")
            continue
        
        cursor.execute("""
            INSERT INTO master.dds_items (code, name_ru, category_id, group_id, sort_order)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id
        """, (code, name, category_id, group_id, idx + 1))
        
        item_ids[code] = cursor.fetchone()[0]
    
    conn.commit()
    print(f"✅ Загружено уникальных статей: {len(item_ids)}")
    
    # Теперь добавляем маппинг для всех вариантов названий
    print("\n📥 Создание маппинга названий...")
    
    mapping_records = []
    for _, row in df.iterrows():
        code = row['Новый код']
        name = row['Название статьи']
        old_id = row.get('ID')
        
        item_id = item_ids.get(code)
        if not item_id:
            continue
        
        mapping_records.append((
            item_id,
            name,
            int(old_id) if pd.notna(old_id) else None,
            'legacy'
        ))
    
    # Удаляем дубликаты по (dds_item_id, old_name)
    seen = set()
    unique_mappings = []
    for rec in mapping_records:
        key = (rec[0], rec[1])  # (item_id, old_name)
        if key not in seen:
            seen.add(key)
            unique_mappings.append(rec)
    
    execute_batch(cursor, """
        INSERT INTO master.dds_items_mapping (dds_item_id, old_name, old_id, source_system)
        VALUES (%s, %s, %s, %s)
        ON CONFLICT (old_name, source_system) DO NOTHING
    """, unique_mappings, page_size=100)
    
    conn.commit()
    print(f"✅ Создано маппингов: {len(unique_mappings)}")
    
    return item_ids

def print_statistics(conn):
    """Статистика"""
    print("\n📊 СТАТИСТИКА")
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) FROM master.dds_categories")
    print(f"Категорий: {cursor.fetchone()[0]}")
    
    cursor.execute("SELECT COUNT(*) FROM master.dds_groups")
    print(f"Групп: {cursor.fetchone()[0]}")
    
    cursor.execute("SELECT COUNT(*) FROM master.dds_items")
    items_count = cursor.fetchone()[0]
    print(f"Уникальных статей: {items_count}")
    
    cursor.execute("SELECT COUNT(*) FROM master.dds_items_mapping")
    mapping_count = cursor.fetchone()[0]
    print(f"Вариантов названий: {mapping_count}")
    
    cursor.execute("""
        SELECT c.name_ru, COUNT(DISTINCT i.id)
        FROM master.dds_categories c
        LEFT JOIN master.dds_items i ON c.id = i.category_id
        GROUP BY c.name_ru, c.sort_order
        ORDER BY c.sort_order
    """)
    print("\nРаспределение по категориям:")
    for cat, cnt in cursor.fetchall():
        print(f"  {cat}: {cnt}")
    
    # Примеры статей с несколькими вариантами
    cursor.execute("""
        SELECT 
            i.code,
            i.name_ru as canonical_name,
            COUNT(m.id) as variants_count,
            STRING_AGG(DISTINCT m.old_name, ' | ') as variants
        FROM master.dds_items i
        JOIN master.dds_items_mapping m ON i.id = m.dds_item_id
        GROUP BY i.code, i.name_ru
        HAVING COUNT(m.id) > 1
        ORDER BY variants_count DESC
        LIMIT 5
    """)
    
    multi_variants = cursor.fetchall()
    if multi_variants:
        print(f"\nСтатьи с несколькими вариантами названий (топ-5):")
        for code, canonical, cnt, variants in multi_variants:
            print(f"  {code} ({cnt} вариантов):")
            print(f"    Основное: {canonical}")
            print(f"    Варианты: {variants[:100]}...")


def main():
    print("=" * 70)
    print("🔄 ЗАГРУЗКА СПРАВОЧНИКА ДДС")
    print("=" * 70)
    
    # Загрузка Excel
    df = load_excel()
    
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
        category_ids = insert_categories(conn, df)
        group_ids = insert_groups(conn, df, category_ids)
        insert_items(conn, df, category_ids, group_ids)
        
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
