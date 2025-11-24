#!/usr/bin/env python3
"""
Загрузка всех справочников master в PostgreSQL:
1. ДДС (dds_categories, dds_groups, dds_items)
2. Затраты (cost_categories, cost_groups, cost_items)
"""

import pandas as pd
import psycopg2
from psycopg2.extras import execute_batch
import sys
from pathlib import Path

# Настройки подключения
DB_CONFIG = {
    'host': 'localhost',
    'port': 5432,
    'database': 'analytics',
    'user': 'analytics_user',
    'password': 'analytics_secure_2025'
}

BASE_DIR = Path('/opt/docagent/data/osv_revenue_0925/input/info_docs/Postgres/correct_2/master_schema_files')

def create_dds_schema(conn):
    """Создание схемы таблиц ДДС"""
    print("\n🏗️  Создание таблиц ДДС...")
    
    cursor = conn.cursor()
    
    sql = Path(BASE_DIR / 'dds_schema_postgresql.sql').read_text()
    
    # Заменим на master. схему
    sql = sql.replace('CREATE TABLE dds_', 'CREATE TABLE IF NOT EXISTS master.dds_')
    sql = sql.replace('CREATE INDEX idx_', 'CREATE INDEX IF NOT EXISTS idx_dds_')
    sql = sql.replace('REFERENCES dds_', 'REFERENCES master.dds_')
    
    try:
        cursor.execute(sql)
        conn.commit()
        print("✅ Таблицы ДДС созданы")
    except Exception as e:
        conn.rollback()
        print(f"❌ Ошибка создания таблиц ДДС: {e}")
        raise

def create_cost_schema(conn):
    """Создание схемы таблиц затрат"""
    print("\n🏗️  Создание таблиц затрат...")
    
    cursor = conn.cursor()
    
    sql = Path(BASE_DIR / 'master_cost_schema.sql').read_text()
    
    try:
        cursor.execute(sql)
        conn.commit()
        print("✅ Таблицы затрат созданы")
    except Exception as e:
        conn.rollback()
        print(f"❌ Ошибка создания таблиц затрат: {e}")
        raise

def load_dds_categories(conn):
    """Загрузка категорий ДДС"""
    print("\n📥 Загрузка категорий ДДС...")
    
    cursor = conn.cursor()
    
    categories = [
        ('OPS_IN',  'Операционная деятельность - Поступления',  'OPERATING',  'inflow',    1, '#C5E0B4'),
        ('OPS_OUT', 'Операционная деятельность - Платежи',     'OPERATING',  'outflow',   2, '#F8CBAD'),
        ('INV_IN',  'Инвестиционная деятельность - Поступления', 'INVESTING',  'inflow',    3, '#B4C7E7'),
        ('INV_OUT', 'Инвестиционная деятельность - Платежи',   'INVESTING',  'outflow',   4, '#FFE699'),
        ('FIN_IN',  'Финансовая деятельность - Поступления',    'FINANCING',  'inflow',    5, '#D9D2E9'),
        ('FIN_OUT', 'Финансовая деятельность - Платежи',       'FINANCING',  'outflow',   6, '#F4B084'),
        ('TRF',     'Внутренние переводы',                      'TRANSFER',   'transfer',  7, '#D9D9D9')
    ]
    
    sql = """
        INSERT INTO master.dds_categories (code, name_ru, activity_type, direction, sort_order, color_hex)
        VALUES (%s, %s, %s, %s, %s, %s)
        ON CONFLICT (code) DO NOTHING
    """
    
    try:
        execute_batch(cursor, sql, categories)
        conn.commit()
        print(f"✅ Загружено категорий: {len(categories)}")
    except Exception as e:
        conn.rollback()
        print(f"❌ Ошибка загрузки категорий ДДС: {e}")
        raise

def load_dds_groups(conn):
    """Загрузка групп ДДС"""
    print("\n📥 Загрузка групп ДДС...")
    
    df = pd.read_csv(BASE_DIR / 'import_2_groups.csv')
    
    cursor = conn.cursor()
    
    # Маппинг группы -> категория
    category_mapping = {
        1: 'OPS_IN', 2: 'OPS_IN', 3: 'OPS_IN', 4: 'OPS_IN', 5: 'OPS_IN',
        6: 'OPS_OUT', 7: 'OPS_OUT', 8: 'OPS_OUT', 9: 'OPS_OUT', 10: 'OPS_OUT',
        11: 'OPS_OUT', 12: 'OPS_OUT', 13: 'OPS_OUT', 14: 'OPS_OUT', 15: 'OPS_OUT', 16: 'OPS_OUT',
        17: 'INV_IN', 18: 'INV_IN', 19: 'INV_IN', 20: 'INV_IN', 21: 'INV_IN',
        22: 'INV_OUT', 23: 'INV_OUT', 24: 'INV_OUT', 25: 'INV_OUT', 26: 'INV_OUT', 27: 'INV_OUT', 28: 'INV_OUT',
        29: 'FIN_IN', 30: 'FIN_IN'
    }
    
    records = []
    for idx, row in df.iterrows():
        group_id = int(row['id'])
        cat_code = category_mapping.get(group_id, 'OPS_IN')
        
        # Получить category_id по коду
        cursor.execute("SELECT id FROM master.dds_categories WHERE code = %s", (cat_code,))
        cat_id = cursor.fetchone()[0]
        
        records.append((
            group_id,
            row['name_ru'],
            cat_id,
            int(row['sort_order'])
        ))
    
    sql = """
        INSERT INTO master.dds_groups (id, name_ru, category_id, sort_order)
        VALUES (%s, %s, %s, %s)
        ON CONFLICT (id) DO UPDATE SET
            name_ru = EXCLUDED.name_ru,
            category_id = EXCLUDED.category_id,
            sort_order = EXCLUDED.sort_order
    """
    
    try:
        execute_batch(cursor, sql, records)
        conn.commit()
        print(f"✅ Загружено групп: {len(records)}")
    except Exception as e:
        conn.rollback()
        print(f"❌ Ошибка загрузки групп ДДС: {e}")
        raise

def load_dds_items(conn):
    """Загрузка статей ДДС"""
    print("\n📥 Загрузка статей ДДС...")
    
    df = pd.read_csv(BASE_DIR / 'nocodb_dds_items_flat.csv')
    
    cursor = conn.cursor()
    
    records = []
    for idx, row in df.iterrows():
        # Получить category_id и group_id
        cursor.execute("SELECT id FROM master.dds_categories WHERE code = %s", (row['category_code'],))
        cat_result = cursor.fetchone()
        if not cat_result:
            print(f"⚠️  Пропуск {row['code']}: категория {row['category_code']} не найдена")
            continue
        cat_id = cat_result[0]
        
        cursor.execute("SELECT id FROM master.dds_groups WHERE name_ru = %s", (row['group_name'],))
        grp_result = cursor.fetchone()
        if not grp_result:
            print(f"⚠️  Пропуск {row['code']}: группа {row['group_name']} не найдена")
            continue
        grp_id = grp_result[0]
        
        records.append((
            row['code'],
            row['name_ru'],
            cat_id,
            grp_id,
            bool(row.get('is_active', True))
        ))
    
    sql = """
        INSERT INTO master.dds_items (code, name_ru, category_id, group_id, is_active)
        VALUES (%s, %s, %s, %s, %s)
        ON CONFLICT (code) DO UPDATE SET
            name_ru = EXCLUDED.name_ru,
            category_id = EXCLUDED.category_id,
            group_id = EXCLUDED.group_id,
            is_active = EXCLUDED.is_active
    """
    
    try:
        execute_batch(cursor, sql, records)
        conn.commit()
        print(f"✅ Загружено статей ДДС: {len(records)}")
    except Exception as e:
        conn.rollback()
        print(f"❌ Ошибка загрузки статей ДДС: {e}")
        raise

def load_cost_categories(conn):
    """Загрузка категорий затрат"""
    print("\n📥 Загрузка категорий затрат...")
    
    df = pd.read_csv(BASE_DIR / 'cost_categories.csv')
    
    cursor = conn.cursor()
    
    records = [(row['code'], row['name_ru'], row['name_en'], row['sort_order']) 
               for idx, row in df.iterrows()]
    
    sql = """
        INSERT INTO master.cost_categories (code, name_ru, name_en, sort_order)
        VALUES (%s, %s, %s, %s)
        ON CONFLICT (code) DO NOTHING
    """
    
    try:
        execute_batch(cursor, sql, records)
        conn.commit()
        print(f"✅ Загружено категорий: {len(records)}")
    except Exception as e:
        conn.rollback()
        print(f"❌ Ошибка загрузки категорий затрат: {e}")
        raise

def load_cost_groups(conn):
    """Загрузка групп затрат"""
    print("\n📥 Загрузка групп затрат...")
    
    df = pd.read_csv(BASE_DIR / 'cost_groups.csv')
    
    cursor = conn.cursor()
    
    records = []
    for idx, row in df.iterrows():
        # Получить category_id
        cursor.execute("SELECT id FROM master.cost_categories WHERE code = %s", (row['category_code'],))
        cat_result = cursor.fetchone()
        if not cat_result:
            continue
        cat_id = cat_result[0]
        
        records.append((
            int(row['id']),
            row['group_code'],
            row['name_ru'],
            cat_id,
            int(row['sort_order'])
        ))
    
    sql = """
        INSERT INTO master.cost_groups (id, group_code, name_ru, category_id, sort_order)
        VALUES (%s, %s, %s, %s, %s)
        ON CONFLICT (id) DO UPDATE SET
            group_code = EXCLUDED.group_code,
            name_ru = EXCLUDED.name_ru,
            category_id = EXCLUDED.category_id,
            sort_order = EXCLUDED.sort_order
    """
    
    try:
        execute_batch(cursor, sql, records)
        conn.commit()
        print(f"✅ Загружено групп: {len(records)}")
    except Exception as e:
        conn.rollback()
        print(f"❌ Ошибка загрузки групп затрат: {e}")
        raise

def load_cost_items(conn):
    """Загрузка статей затрат"""
    print("\n📥 Загрузка статей затрат...")
    
    df = pd.read_csv(BASE_DIR / 'nocodb_cost_items_flat.csv')
    
    cursor = conn.cursor()
    
    records = []
    for idx, row in df.iterrows():
        # Получить category_id и group_id
        cursor.execute("SELECT id FROM master.cost_categories WHERE code = %s", (row['category_code'],))
        cat_result = cursor.fetchone()
        if not cat_result:
            print(f"⚠️  Пропуск {row['code']}: категория не найдена")
            continue
        cat_id = cat_result[0]
        
        cursor.execute("SELECT id FROM master.cost_groups WHERE group_code = %s", (row['group_code'],))
        grp_result = cursor.fetchone()
        if not grp_result:
            print(f"⚠️  Пропуск {row['code']}: группа не найдена")
            continue
        grp_id = grp_result[0]
        
        records.append((
            row['code'],
            row['name_ru'],
            cat_id,
            grp_id,
            row.get('pl_block', None),
            bool(row.get('is_active', True))
        ))
    
    sql = """
        INSERT INTO master.cost_items (code, name_ru, category_id, group_id, pl_block, is_active)
        VALUES (%s, %s, %s, %s, %s, %s)
        ON CONFLICT (code) DO UPDATE SET
            name_ru = EXCLUDED.name_ru,
            category_id = EXCLUDED.category_id,
            group_id = EXCLUDED.group_id,
            pl_block = EXCLUDED.pl_block,
            is_active = EXCLUDED.is_active
    """
    
    try:
        execute_batch(cursor, sql, records)
        conn.commit()
        print(f"✅ Загружено статей затрат: {len(records)}")
    except Exception as e:
        conn.rollback()
        print(f"❌ Ошибка загрузки статей затрат: {e}")
        raise

def print_statistics(conn):
    """Вывод статистики"""
    print("\n" + "="*60)
    print("📊 СТАТИСТИКА СПРАВОЧНИКОВ")
    print("="*60)
    
    cursor = conn.cursor()
    
    stats = [
        ("ДДС: Категории", "SELECT COUNT(*) FROM master.dds_categories"),
        ("ДДС: Группы", "SELECT COUNT(*) FROM master.dds_groups"),
        ("ДДС: Статьи", "SELECT COUNT(*) FROM master.dds_items"),
        ("Затраты: Категории", "SELECT COUNT(*) FROM master.cost_categories"),
        ("Затраты: Группы", "SELECT COUNT(*) FROM master.cost_groups"),
        ("Затраты: Статьи", "SELECT COUNT(*) FROM master.cost_items"),
    ]
    
    for name, sql in stats:
        cursor.execute(sql)
        count = cursor.fetchone()[0]
        print(f"{name:25} {count:5}")
    
    print("="*60)

def main():
    """Основная функция"""
    print("="*60)
    print("🔄 ЗАГРУЗКА СПРАВОЧНИКОВ MASTER")
    print("="*60)
    
    # Проверка файлов
    if not BASE_DIR.exists():
        print(f"❌ Директория не найдена: {BASE_DIR}")
        sys.exit(1)
    
    # Подключение к БД
    print("\n🔌 Подключение к PostgreSQL...")
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        print("✅ Подключено")
    except Exception as e:
        print(f"❌ Ошибка подключения: {e}")
        sys.exit(1)
    
    try:
        # Создание схем
        create_dds_schema(conn)
        create_cost_schema(conn)
        
        # Загрузка ДДС
        load_dds_categories(conn)
        load_dds_groups(conn)
        load_dds_items(conn)
        
        # Загрузка затрат
        load_cost_categories(conn)
        load_cost_groups(conn)
        load_cost_items(conn)
        
        # Статистика
        print_statistics(conn)
        
        print("\n✅ ЗАГРУЗКА ЗАВЕРШЕНА УСПЕШНО")
        
    except Exception as e:
        print(f"\n❌ ОШИБКА: {e}")
        sys.exit(1)
    
    finally:
        conn.close()

if __name__ == '__main__':
    main()
