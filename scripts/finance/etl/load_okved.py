#!/usr/bin/env python3
"""
Загрузка справочника ОКВЭД 2 и добавление связей с компаниями/контрагентами
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

OKVED_FILE = '/tmp/okved/okved_2.xls'

def load_okved_file():
    """Загрузка файла ОКВЭД"""
    print(f"📄 Чтение: {OKVED_FILE}")
    
    df = pd.read_excel(OKVED_FILE, engine='xlrd')
    
    print(f"✅ Загружено записей: {len(df)}")
    
    # Статистика по уровням
    df['level'] = df['code'].apply(lambda x: determine_level(str(x)))
    level_counts = df['level'].value_counts().sort_index()
    print("\nУровни иерархии:")
    for level, count in level_counts.items():
        print(f"  Уровень {level}: {count}")
    
    return df

def determine_level(code):
    """Определение уровня иерархии ОКВЭД"""
    code = str(code).strip()
    
    # Раздел (буква A-U)
    if len(code) == 1 and code.isalpha():
        return 1
    
    # Уровень 2: XX (01, 62, 95)
    if len(code) == 2 and code.replace('.', '').isdigit():
        return 2
    
    # Уровень 3: XX.X (01.1, 62.0)
    if len(code) == 4 and code[2] == '.':
        return 3
    
    # Уровень 4: XX.XX (01.11, 62.01)
    if len(code) == 5 and code[2] == '.':
        return 4
    
    # Уровень 5: XX.XX.X (01.11.1)
    if len(code) == 7 and code[2] == '.' and code[5] == '.':
        return 5
    
    # Уровень 6: XX.XX.XX (01.11.11)
    if len(code) == 8 and code[2] == '.' and code[5] == '.':
        return 6
    
    return 0

def create_schema(conn):
    """Создание схемы ОКВЭД и связей"""
    print("\n📐 Создание схемы...")
    cursor = conn.cursor()
    
    schema = """
    -- Справочник ОКВЭД 2
    CREATE TABLE IF NOT EXISTS master.okved (
        id SERIAL PRIMARY KEY,
        code VARCHAR(20) UNIQUE NOT NULL,
        parent_code VARCHAR(20),
        section VARCHAR(1),
        name VARCHAR(1000) NOT NULL,
        comment TEXT,
        level INTEGER NOT NULL,
        is_active BOOLEAN DEFAULT TRUE,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    -- Связь компаний с ОКВЭД
    CREATE TABLE IF NOT EXISTS master.companies_okved (
        id SERIAL PRIMARY KEY,
        company_id INTEGER NOT NULL REFERENCES master.companies(id) ON DELETE CASCADE,
        okved_code VARCHAR(20) NOT NULL,
        okved_id INTEGER REFERENCES master.okved(id) ON DELETE CASCADE,
        is_primary BOOLEAN DEFAULT FALSE,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(company_id, okved_code)
    );

    -- Связь контрагентов с ОКВЭД
    CREATE TABLE IF NOT EXISTS master.counterparties_okved (
        id SERIAL PRIMARY KEY,
        counterparty_id INTEGER NOT NULL REFERENCES master.counterparties(id) ON DELETE CASCADE,
        okved_code VARCHAR(20) NOT NULL,
        okved_id INTEGER REFERENCES master.okved(id) ON DELETE CASCADE,
        is_primary BOOLEAN DEFAULT FALSE,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(counterparty_id, okved_code)
    );

    -- Добавление колонки primary_okved в companies
    ALTER TABLE master.companies 
    ADD COLUMN IF NOT EXISTS primary_okved VARCHAR(20);

    -- Добавление колонки primary_okved в counterparties
    ALTER TABLE master.counterparties 
    ADD COLUMN IF NOT EXISTS primary_okved VARCHAR(20);

    -- Индексы
    CREATE INDEX IF NOT EXISTS idx_okved_code ON master.okved(code);
    CREATE INDEX IF NOT EXISTS idx_okved_parent ON master.okved(parent_code);
    CREATE INDEX IF NOT EXISTS idx_okved_section ON master.okved(section);
    CREATE INDEX IF NOT EXISTS idx_okved_level ON master.okved(level);
    CREATE INDEX IF NOT EXISTS idx_companies_okved_company ON master.companies_okved(company_id);
    CREATE INDEX IF NOT EXISTS idx_companies_okved_code ON master.companies_okved(okved_code);
    CREATE INDEX IF NOT EXISTS idx_counterparties_okved_counterparty ON master.counterparties_okved(counterparty_id);
    CREATE INDEX IF NOT EXISTS idx_counterparties_okved_code ON master.counterparties_okved(okved_code);
    CREATE INDEX IF NOT EXISTS idx_companies_primary_okved ON master.companies(primary_okved);
    CREATE INDEX IF NOT EXISTS idx_counterparties_primary_okved ON master.counterparties(primary_okved);

    -- Комментарии
    COMMENT ON TABLE master.okved IS 'Классификатор ОКВЭД 2 (полный справочник)';
    COMMENT ON TABLE master.companies_okved IS 'Связь компаний группы с кодами ОКВЭД (может быть несколько)';
    COMMENT ON TABLE master.counterparties_okved IS 'Связь контрагентов с кодами ОКВЭД (может быть несколько)';
    COMMENT ON COLUMN master.companies.primary_okved IS 'Основной ОКВЭД компании';
    COMMENT ON COLUMN master.counterparties.primary_okved IS 'Основной ОКВЭД контрагента';
    """
    
    try:
        cursor.execute(schema)
        conn.commit()
        print("✅ Схема создана")
    except Exception as e:
        conn.rollback()
        print(f"❌ Ошибка: {e}")
        raise

def insert_okved(conn, df):
    """Вставка справочника ОКВЭД"""
    print("\n📥 Загрузка ОКВЭД...")
    cursor = conn.cursor()
    
    # Очистка старых данных
    cursor.execute("TRUNCATE TABLE master.okved CASCADE")
    
    records = []
    for _, row in df.iterrows():
        code = str(row['code']).strip()
        parent_code = str(row['parent_code']).strip() if pd.notna(row['parent_code']) else None
        section = str(row['section']).strip() if pd.notna(row['section']) else None
        name = str(row['name']).strip()
        comment = str(row['comment']).strip() if pd.notna(row['comment']) else None
        level = determine_level(code)
        
        records.append((code, parent_code, section, name, comment, level))
    
    execute_batch(cursor, """
        INSERT INTO master.okved (code, parent_code, section, name, comment, level)
        VALUES (%s, %s, %s, %s, %s, %s)
    """, records, page_size=500)
    
    conn.commit()
    print(f"✅ Загружено кодов ОКВЭД: {len(records)}")

def print_statistics(conn):
    """Статистика"""
    print("\n📊 СТАТИСТИКА")
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) FROM master.okved")
    print(f"Всего кодов ОКВЭД: {cursor.fetchone()[0]}")
    
    cursor.execute("""
        SELECT level, COUNT(*) 
        FROM master.okved 
        GROUP BY level 
        ORDER BY level
    """)
    print("\nПо уровням:")
    level_names = {
        1: 'Раздел (буква)',
        2: 'Класс (XX)',
        3: 'Подкласс (XX.X)',
        4: 'Группа (XX.XX)',
        5: 'Подгруппа (XX.XX.X)',
        6: 'Вид (XX.XX.XX)'
    }
    for level, count in cursor.fetchall():
        print(f"  {level_names.get(level, f'Уровень {level}')}: {count}")
    
    # Примеры разделов
    cursor.execute("""
        SELECT code, name 
        FROM master.okved 
        WHERE level = 1 
        ORDER BY code 
        LIMIT 5
    """)
    print("\nПримеры разделов:")
    for code, name in cursor.fetchall():
        print(f"  {code}: {name[:60]}...")
    
    # Примеры детальных кодов
    cursor.execute("""
        SELECT code, name 
        FROM master.okved 
        WHERE level = 4 AND code LIKE '62%'
        ORDER BY code 
        LIMIT 3
    """)
    print("\nПримеры детальных кодов (IT-сектор):")
    for code, name in cursor.fetchall():
        print(f"  {code}: {name[:60]}...")

def main():
    print("=" * 70)
    print("🔄 ЗАГРУЗКА СПРАВОЧНИКА ОКВЭД 2")
    print("=" * 70)
    
    # Загрузка файла
    df = load_okved_file()
    
    # Подключение
    print("\n🔌 Подключение к PostgreSQL...")
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        print("✅ Подключено")
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        sys.exit(1)
    
    try:
        # 1. Создание схемы
        create_schema(conn)
        
        # 2. Загрузка данных
        insert_okved(conn, df)
        
        # 3. Статистика
        print_statistics(conn)
        
        print("\n" + "=" * 70)
        print("✅ ЗАГРУЗКА ЗАВЕРШЕНА УСПЕШНО")
        print("=" * 70)
        print("\n💡 Следующие шаги:")
        print("1. Заполните primary_okved для компаний через DaData или вручную")
        print("2. Используйте companies_okved для дополнительных кодов")
        print("3. Заполните ОКВЭД для контрагентов из DaData")
        
    except Exception as e:
        print(f"\n❌ ОШИБКА: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        conn.close()

if __name__ == '__main__':
    main()
