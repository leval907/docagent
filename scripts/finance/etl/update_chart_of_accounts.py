#!/usr/bin/env python3
"""
Обновление справочника плана счетов (master.chart_of_accounts)
Полная очистка и загрузка из Excel файла с расширенной структурой
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

EXCEL_FILE = '/opt/docagent/data/osv_revenue_0925/input/info_docs/Postgres/correct_2/chart_of_accounts_master_structured_3.xlsx'

def clean_value(val):
    """Очистка значений от NaN"""
    if pd.isna(val):
        return None
    if isinstance(val, str):
        return val.strip()
    if isinstance(val, bool):
        return val
    if isinstance(val, (int, float)):
        return val
    return str(val)

def load_excel_data():
    """Загрузка данных из Excel"""
    print(f"📄 Чтение файла: {EXCEL_FILE}")
    df = pd.read_excel(EXCEL_FILE)
    
    print(f"✅ Загружено строк: {len(df)}")
    print(f"Колонки: {list(df.columns)}")
    
    return df

def clear_chart_of_accounts(conn):
    """Очистка таблицы chart_of_accounts"""
    print("\n🗑️  Очистка таблицы master.chart_of_accounts...")
    
    cursor = conn.cursor()
    
    try:
        # Сначала очистим зависимые данные в history.osv_detail
        cursor.execute("SELECT COUNT(*) FROM history.osv_detail")
        osv_count = cursor.fetchone()[0]
        print(f"   История: {osv_count} записей в osv_detail")
        
        # Очистка chart_of_accounts (CASCADE удалит связи)
        cursor.execute("TRUNCATE TABLE master.chart_of_accounts RESTART IDENTITY CASCADE")
        conn.commit()
        
        print("✅ Таблица очищена")
        
    except Exception as e:
        conn.rollback()
        print(f"❌ Ошибка очистки: {e}")
        raise

def update_schema(conn):
    """Обновление схемы таблицы с новыми колонками"""
    print("\n🔧 Обновление схемы таблицы...")
    
    cursor = conn.cursor()
    
    # Новые колонки из файла
    new_columns = [
        "ALTER TABLE master.chart_of_accounts ADD COLUMN IF NOT EXISTS subconto1 VARCHAR(200)",
        "ALTER TABLE master.chart_of_accounts ADD COLUMN IF NOT EXISTS subconto2 VARCHAR(200)",
        "ALTER TABLE master.chart_of_accounts ADD COLUMN IF NOT EXISTS subconto3 VARCHAR(200)",
        "ALTER TABLE master.chart_of_accounts ADD COLUMN IF NOT EXISTS rsbu_type VARCHAR(20)",
        "ALTER TABLE master.chart_of_accounts ADD COLUMN IF NOT EXISTS balance_flag BOOLEAN DEFAULT FALSE",
        "ALTER TABLE master.chart_of_accounts ADD COLUMN IF NOT EXISTS pnl_flag BOOLEAN DEFAULT FALSE",
        "ALTER TABLE master.chart_of_accounts ADD COLUMN IF NOT EXISTS liquidity_group VARCHAR(20)",
        "ALTER TABLE master.chart_of_accounts ADD COLUMN IF NOT EXISTS maturity_group VARCHAR(20)",
        "ALTER TABLE master.chart_of_accounts ADD COLUMN IF NOT EXISTS wc_role VARCHAR(50)",
        "ALTER TABLE master.chart_of_accounts ADD COLUMN IF NOT EXISTS balance_equation_class VARCHAR(50)",
        "ALTER TABLE master.chart_of_accounts ADD COLUMN IF NOT EXISTS balance_mgmt_group VARCHAR(50)"
    ]
    
    try:
        for sql in new_columns:
            cursor.execute(sql)
        
        conn.commit()
        print("✅ Схема обновлена")
        
    except Exception as e:
        conn.rollback()
        print(f"❌ Ошибка обновления схемы: {e}")
        raise

def insert_chart_of_accounts(conn, df):
    """Вставка данных плана счетов"""
    print(f"\n📥 Загрузка {len(df)} счетов...")
    
    cursor = conn.cursor()
    
    insert_sql = """
        INSERT INTO master.chart_of_accounts (
            account_code,
            account_name,
            account_level,
            parent_code,
            subconto1,
            subconto2,
            subconto3,
            rsbu_type,
            account_type,
            balance_type,
            balance_flag,
            pnl_flag,
            liquidity_group,
            maturity_group,
            wc_role,
            balance_equation_class,
            balance_mgmt_group,
            is_active
        ) VALUES (
            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
        )
    """
    
    # Подготовка данных
    records = []
    for idx, row in df.iterrows():
        # Определение balance_type по account_type
        balance_type = None
        account_type = clean_value(row.get('account_type'))
        if account_type == 'ASSET':
            balance_type = 'debit'
        elif account_type == 'LIABILITY':
            balance_type = 'credit'
        elif account_type == 'EQUITY':
            balance_type = 'credit'
        
        record = (
            clean_value(row['account_code']),
            clean_value(row['account_name']),
            int(row['account_level']) if pd.notna(row['account_level']) else 0,
            clean_value(row.get('parent_code')),
            clean_value(row.get('subconto1')),
            clean_value(row.get('subconto2')),
            clean_value(row.get('subconto3')),
            clean_value(row.get('rsbu_type')),
            clean_value(row.get('account_type')),
            balance_type,
            bool(row.get('balance_flag', False)),
            bool(row.get('pnl_flag', False)),
            clean_value(row.get('liquidity_group')),
            clean_value(row.get('maturity_group')),
            clean_value(row.get('wc_role')),
            clean_value(row.get('balance_equation_class')),
            clean_value(row.get('balance_mgmt_group')),
            True  # is_active
        )
        records.append(record)
    
    try:
        execute_batch(cursor, insert_sql, records, page_size=100)
        conn.commit()
        
        print(f"✅ Загружено счетов: {len(records)}")
        
        # Статистика
        cursor.execute("SELECT COUNT(*) FROM master.chart_of_accounts")
        total = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM master.chart_of_accounts WHERE liquidity_group IS NOT NULL")
        with_liquidity = cursor.fetchone()[0]
        
        cursor.execute("SELECT liquidity_group, COUNT(*) FROM master.chart_of_accounts WHERE liquidity_group IS NOT NULL GROUP BY liquidity_group ORDER BY liquidity_group")
        liquidity_groups = cursor.fetchall()
        
        print(f"\n📊 Статистика:")
        print(f"   Всего счетов: {total}")
        print(f"   С группами ликвидности: {with_liquidity}")
        print(f"\n   Группы ликвидности:")
        for group, count in liquidity_groups:
            print(f"     {group}: {count} счетов")
        
    except Exception as e:
        conn.rollback()
        print(f"❌ Ошибка вставки: {e}")
        raise

def main():
    """Основная функция"""
    print("=" * 60)
    print("🔄 ОБНОВЛЕНИЕ ПЛАНА СЧЕТОВ (master.chart_of_accounts)")
    print("=" * 60)
    
    # Проверка файла
    if not Path(EXCEL_FILE).exists():
        print(f"❌ Файл не найден: {EXCEL_FILE}")
        sys.exit(1)
    
    # Загрузка данных из Excel
    df = load_excel_data()
    
    # Подключение к БД
    print("\n🔌 Подключение к PostgreSQL...")
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        print("✅ Подключено")
    except Exception as e:
        print(f"❌ Ошибка подключения: {e}")
        sys.exit(1)
    
    try:
        # 1. Обновление схемы
        update_schema(conn)
        
        # 2. Очистка таблицы
        clear_chart_of_accounts(conn)
        
        # 3. Загрузка новых данных
        insert_chart_of_accounts(conn, df)
        
        print("\n" + "=" * 60)
        print("✅ ОБНОВЛЕНИЕ ЗАВЕРШЕНО УСПЕШНО")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ ОШИБКА: {e}")
        sys.exit(1)
    
    finally:
        conn.close()

if __name__ == '__main__':
    main()
