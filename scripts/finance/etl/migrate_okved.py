#!/usr/bin/env python3
"""
Заполнение ОКВЭД для компаний из существующего поля okved
"""

import psycopg2
from psycopg2.extras import execute_batch

DB_CONFIG = {
    'host': 'localhost',
    'port': 5432,
    'database': 'analytics',
    'user': 'analytics_user',
    'password': 'analytics_secure_2025'
}

def migrate_company_okved(conn):
    """Миграция ОКВЭД из старого поля okved в primary_okved"""
    print("\n📋 Миграция ОКВЭД компаний...")
    cursor = conn.cursor()
    
    # Обновляем primary_okved из okved где есть данные
    cursor.execute("""
        UPDATE master.companies
        SET primary_okved = okved
        WHERE okved IS NOT NULL 
        AND okved != ''
        AND primary_okved IS NULL
    """)
    
    updated = cursor.rowcount
    conn.commit()
    
    print(f"✅ Обновлено компаний: {updated}")
    
    # Статистика
    cursor.execute("""
        SELECT 
            COUNT(*) AS total,
            COUNT(primary_okved) AS with_okved,
            COUNT(primary_okved) * 100.0 / COUNT(*) AS coverage
        FROM master.companies
    """)
    
    total, with_okved, coverage = cursor.fetchone()
    print(f"\nПокрытие ОКВЭД:")
    print(f"  Всего компаний: {total}")
    print(f"  С ОКВЭД: {with_okved} ({coverage:.1f}%)")
    print(f"  Без ОКВЭД: {total - with_okved}")
    
    # Примеры компаний с ОКВЭД
    cursor.execute("""
        SELECT company_name, inn, primary_okved, primary_okved_name
        FROM master.v_companies_with_okved
        WHERE primary_okved IS NOT NULL
        LIMIT 5
    """)
    
    print("\nПримеры компаний с ОКВЭД:")
    for name, inn, code, okved_name in cursor.fetchall():
        print(f"  • {name[:40]}")
        print(f"    ИНН: {inn}, ОКВЭД: {code}")
        print(f"    {okved_name[:70]}")

def migrate_counterparty_okved(conn):
    """Миграция ОКВЭД контрагентов из DaData enrichment"""
    print("\n\n📋 Миграция ОКВЭД контрагентов...")
    cursor = conn.cursor()
    
    # Проверяем есть ли поле okved в counterparties
    cursor.execute("""
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_schema = 'master' 
        AND table_name = 'counterparties'
        AND column_name IN ('okved', 'okved_code')
    """)
    
    okved_col = cursor.fetchone()
    
    if not okved_col:
        print("⚠️  Поле okved не найдено в counterparties")
        print("💡 ОКВЭД можно будет добавить через DaData enrichment")
        return
    
    col_name = okved_col[0]
    
    # Обновляем primary_okved
    cursor.execute(f"""
        UPDATE master.counterparties
        SET primary_okved = {col_name}
        WHERE {col_name} IS NOT NULL 
        AND {col_name} != ''
        AND primary_okved IS NULL
    """)
    
    updated = cursor.rowcount
    conn.commit()
    
    print(f"✅ Обновлено контрагентов: {updated}")
    
    # Статистика
    cursor.execute("""
        SELECT 
            COUNT(*) AS total,
            COUNT(primary_okved) AS with_okved,
            COUNT(primary_okved) * 100.0 / COUNT(*) AS coverage
        FROM master.counterparties
    """)
    
    total, with_okved, coverage = cursor.fetchone()
    print(f"\nПокрытие ОКВЭД контрагентов:")
    print(f"  Всего: {total}")
    print(f"  С ОКВЭД: {with_okved} ({coverage:.1f}%)")
    print(f"  Без ОКВЭД: {total - with_okved}")

def analyze_okved_distribution(conn):
    """Анализ распределения ОКВЭД"""
    print("\n\n📊 АНАЛИЗ РАСПРЕДЕЛЕНИЯ ПО РАЗДЕЛАМ ОКВЭД")
    print("=" * 70)
    cursor = conn.cursor()
    
    # Распределение компаний по разделам
    cursor.execute("""
        SELECT 
            o.section,
            MAX(o_section.name) AS section_name,
            COUNT(*) AS companies_count
        FROM master.companies c
        INNER JOIN master.okved o ON c.primary_okved = o.code
        LEFT JOIN master.okved o_section ON o.section = o_section.code AND o_section.level = 1
        WHERE c.primary_okved IS NOT NULL
        GROUP BY o.section
        ORDER BY companies_count DESC
        LIMIT 10
    """)
    
    print("\nТоп-10 разделов (компании группы):")
    for section, name, count in cursor.fetchall():
        name_short = name[:50] if name else 'Без названия'
        print(f"  {section}: {name_short}")
        print(f"      Компаний: {count}")
    
    # Самые популярные детальные коды
    cursor.execute("""
        SELECT 
            c.primary_okved,
            o.name,
            COUNT(*) AS count
        FROM master.companies c
        INNER JOIN master.okved o ON c.primary_okved = o.code
        WHERE c.primary_okved IS NOT NULL
        GROUP BY c.primary_okved, o.name
        ORDER BY count DESC
        LIMIT 5
    """)
    
    print("\n\nСамые популярные коды ОКВЭД:")
    for code, name, count in cursor.fetchall():
        print(f"  {code}: {name[:60]}")
        print(f"      Компаний: {count}")

def main():
    print("=" * 70)
    print("🔄 МИГРАЦИЯ ОКВЭД ИЗ СУЩЕСТВУЮЩИХ ДАННЫХ")
    print("=" * 70)
    
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        print("✅ Подключено к БД")
        
        # 1. Миграция компаний
        migrate_company_okved(conn)
        
        # 2. Миграция контрагентов
        migrate_counterparty_okved(conn)
        
        # 3. Анализ распределения
        analyze_okved_distribution(conn)
        
        print("\n" + "=" * 70)
        print("✅ МИГРАЦИЯ ЗАВЕРШЕНА")
        print("=" * 70)
        
    except Exception as e:
        print(f"\n❌ ОШИБКА: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == '__main__':
    main()
