#!/usr/bin/env python3
"""
Загрузка справочника кодов строк отчетности РСБУ
(Баланс, ОФР, ОДК, ОИК и прочие формы)
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

RSBU_FILE = '/tmp/account_codes/account_codes.xls'

def determine_form_and_type(code: int, name: str) -> tuple:
    """Определение формы отчетности и типа строки"""
    
    # Форма отчетности
    if 1000 <= code <= 1699:
        form = 'БАЛАНС'
        section = 'АКТИВ'
    elif 1700 <= code <= 1999:
        form = 'БАЛАНС'
        section = 'ПАССИВ'
    elif 2000 <= code <= 2999:
        form = 'ОФР'
        section = 'ОФР'
    elif 3000 <= code <= 3999:
        form = 'ОИК'
        section = 'КАПИТАЛ'
    elif 4000 <= code <= 4999:
        form = 'ОДК'
        section = 'ДЕНЕЖНЫЕ ПОТОКИ'
    elif 5000 <= code <= 5999:
        form = 'ОЦИ'
        section = 'ЦЕЛЕВЫЕ СРЕДСТВА'
    elif 6000 <= code <= 6999:
        form = 'ОЦИ'
        section = 'ЦЕЛЕВЫЕ СРЕДСТВА'
    else:
        form = 'ПРОЧЕЕ'
        section = 'ПРОЧЕЕ'
    
    # Тип строки
    name_lower = name.lower()
    if 'итого' in name_lower or 'всего' in name_lower:
        row_type = 'ИТОГО'
    elif 'результат' in name_lower or 'прибыль' in name_lower or 'убыток' in name_lower:
        row_type = 'РЕЗУЛЬТАТ'
    elif 'сальдо' in name_lower:
        row_type = 'САЛЬДО'
    elif 'валовая' in name_lower:
        row_type = 'ПОКАЗАТЕЛЬ'
    else:
        row_type = 'СТАТЬЯ'
    
    # Признак расчетной строки (итоговые/результирующие)
    is_calculated = row_type in ['ИТОГО', 'РЕЗУЛЬТАТ', 'САЛЬДО']
    
    return form, section, row_type, is_calculated

def create_schema(conn):
    """Создание схемы для кодов РСБУ"""
    print("\n📐 Создание схемы...")
    cursor = conn.cursor()
    
    schema = """
    -- Справочник кодов строк отчетности РСБУ
    CREATE TABLE IF NOT EXISTS master.rsbu_codes (
        id SERIAL PRIMARY KEY,
        code INTEGER UNIQUE NOT NULL,
        name VARCHAR(500) NOT NULL,
        form VARCHAR(50) NOT NULL,          -- БАЛАНС, ОФР, ОДК, ОИК, ОЦИ
        section VARCHAR(100),                -- АКТИВ, ПАССИВ, КАПИТАЛ и т.д.
        row_type VARCHAR(50),                -- СТАТЬЯ, ИТОГО, РЕЗУЛЬТАТ, САЛЬДО
        is_calculated BOOLEAN DEFAULT FALSE, -- Расчетная строка (итоги)
        is_active BOOLEAN DEFAULT TRUE,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    -- Индексы
    CREATE INDEX IF NOT EXISTS idx_rsbu_codes_code ON master.rsbu_codes(code);
    CREATE INDEX IF NOT EXISTS idx_rsbu_codes_form ON master.rsbu_codes(form);
    CREATE INDEX IF NOT EXISTS idx_rsbu_codes_section ON master.rsbu_codes(section);
    CREATE INDEX IF NOT EXISTS idx_rsbu_codes_type ON master.rsbu_codes(row_type);

    -- Комментарии
    COMMENT ON TABLE master.rsbu_codes IS 
    'Справочник кодов строк бухгалтерской отчетности РСБУ (Баланс, ОФР, ОДК, ОИК)';
    COMMENT ON COLUMN master.rsbu_codes.form IS 
    'Форма отчетности: БАЛАНС, ОФР, ОДК, ОИК, ОЦИ';
    COMMENT ON COLUMN master.rsbu_codes.section IS 
    'Раздел отчетности: АКТИВ, ПАССИВ, КАПИТАЛ, ДЕНЕЖНЫЕ ПОТОКИ и т.д.';
    COMMENT ON COLUMN master.rsbu_codes.row_type IS 
    'Тип строки: СТАТЬЯ (детальная), ИТОГО, РЕЗУЛЬТАТ, САЛЬДО';
    COMMENT ON COLUMN master.rsbu_codes.is_calculated IS 
    'Признак расчетной строки (итоги, результаты, сальдо)';
    """
    
    try:
        cursor.execute(schema)
        conn.commit()
        print("✅ Схема создана")
    except Exception as e:
        conn.rollback()
        print(f"❌ Ошибка: {e}")
        raise

def load_rsbu_codes(conn, df):
    """Загрузка кодов РСБУ"""
    print("\n📥 Загрузка кодов РСБУ...")
    cursor = conn.cursor()
    
    # Очистка старых данных
    cursor.execute("TRUNCATE TABLE master.rsbu_codes CASCADE")
    
    records = []
    for _, row in df.iterrows():
        code = int(row['code'])
        name = str(row['name']).strip()
        
        form, section, row_type, is_calculated = determine_form_and_type(code, name)
        
        records.append((code, name, form, section, row_type, is_calculated))
    
    execute_batch(cursor, """
        INSERT INTO master.rsbu_codes 
        (code, name, form, section, row_type, is_calculated)
        VALUES (%s, %s, %s, %s, %s, %s)
    """, records, page_size=100)
    
    conn.commit()
    print(f"✅ Загружено кодов: {len(records)}")

def print_statistics(conn):
    """Статистика"""
    print("\n📊 СТАТИСТИКА")
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) FROM master.rsbu_codes")
    print(f"Всего кодов: {cursor.fetchone()[0]}")
    
    # По формам
    cursor.execute("""
        SELECT form, COUNT(*) 
        FROM master.rsbu_codes 
        GROUP BY form 
        ORDER BY form
    """)
    print("\nПо формам отчетности:")
    for form, count in cursor.fetchall():
        print(f"  {form}: {count} кодов")
    
    # По типам строк
    cursor.execute("""
        SELECT row_type, COUNT(*) 
        FROM master.rsbu_codes 
        GROUP BY row_type 
        ORDER BY COUNT(*) DESC
    """)
    print("\nПо типам строк:")
    for row_type, count in cursor.fetchall():
        print(f"  {row_type}: {count} кодов")
    
    # Примеры по формам
    print("\nПримеры кодов по формам:")
    
    for form in ['БАЛАНС', 'ОФР', 'ОДК', 'ОИК']:
        cursor.execute("""
            SELECT code, name, section, row_type
            FROM master.rsbu_codes 
            WHERE form = %s
            ORDER BY code 
            LIMIT 3
        """, (form,))
        
        print(f"\n{form}:")
        for code, name, section, row_type in cursor.fetchall():
            print(f"  {code} [{section}] {name[:55]}")
            print(f"        Тип: {row_type}")

def main():
    print("=" * 70)
    print("🔄 ЗАГРУЗКА СПРАВОЧНИКА КОДОВ РСБУ")
    print("=" * 70)
    
    # Загрузка файла
    print(f"\n📄 Чтение: {RSBU_FILE}")
    try:
        df = pd.read_excel(RSBU_FILE, engine='xlrd')
        print(f"✅ Загружено записей: {len(df)}")
    except Exception as e:
        print(f"❌ Ошибка чтения файла: {e}")
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
        # 1. Создание схемы
        create_schema(conn)
        
        # 2. Загрузка данных
        load_rsbu_codes(conn, df)
        
        # 3. Статистика
        print_statistics(conn)
        
        print("\n" + "=" * 70)
        print("✅ ЗАГРУЗКА ЗАВЕРШЕНА УСПЕШНО")
        print("=" * 70)
        print("\n💡 Использование:")
        print("1. Связь с chart_of_accounts через маппинг счетов")
        print("2. Автоматическое формирование отчетных форм")
        print("3. Валидация структуры отчетности")
        
    except Exception as e:
        print(f"\n❌ ОШИБКА: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        conn.close()

if __name__ == '__main__':
    main()
