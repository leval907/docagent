#!/usr/bin/env python3
"""
Скрипт для проверки согласованности списка компаний группы между:
1. Excel файлом (источник истины): data/osv_revenue_0925/input/Группа Компаний_А.xlsx
2. DuckDB (таблица group_companies)
3. ArangoDB (коллекция Companies)
"""

import pandas as pd
import duckdb
from pathlib import Path
import sys
import os

# Добавляем путь к корню проекта для импорта finance_core
sys.path.append('/opt/docagent')
from finance_core.db.connector import DBManager

# === Настройки ===
EXCEL_PATH = Path("/opt/docagent/data/osv_revenue_0925/input/Группа Компаний_А.xlsx")
DUCKDB_PATH = Path("/opt/docagent/knowledge_base/duckdb/osv/osv_database.duckdb")

def normalize_name(name):
    """Нормализация имени для сравнения"""
    if not isinstance(name, str):
        return ""
    return name.strip().upper().replace('"', '').replace("'", "")

def main():
    print("="*80)
    print("🔍 Проверка согласованности компаний группы")
    print("="*80)

    # 1. Загрузка из Excel
    if not EXCEL_PATH.exists():
        print(f"❌ Файл не найден: {EXCEL_PATH}")
        return

    print(f"📂 Чтение Excel: {EXCEL_PATH.name}")
    try:
        df_excel = pd.read_excel(EXCEL_PATH)
        # Предполагаем, что колонка называется 'Группа компаний' или берем первую
        col_name = 'Группа компаний' if 'Группа компаний' in df_excel.columns else df_excel.columns[0]
        excel_companies = [normalize_name(n) for n in df_excel[col_name].dropna().tolist()]
        print(f"   ✅ Найдено {len(excel_companies)} компаний в Excel")
    except Exception as e:
        print(f"   ❌ Ошибка чтения Excel: {e}")
        return

    # 2. Загрузка из DuckDB
    print(f"\n🦆 Чтение DuckDB: {DUCKDB_PATH.name}")
    duckdb_companies = []
    try:
        conn = duckdb.connect(str(DUCKDB_PATH))
        # Проверяем наличие таблицы
        tables = [t[0] for t in conn.execute("SHOW TABLES").fetchall()]
        
        if 'group_companies' in tables:
            df_duck = conn.execute("SELECT * FROM group_companies").fetchdf()
            # Берем первую колонку
            duckdb_companies = [normalize_name(n) for n in df_duck.iloc[:, 0].dropna().tolist()]
            print(f"   ✅ Найдено {len(duckdb_companies)} компаний в таблице group_companies")
        else:
            print("   ❌ Таблица group_companies не найдена!")
        
        conn.close()
    except Exception as e:
        print(f"   ❌ Ошибка чтения DuckDB: {e}")

    # 3. Загрузка из ArangoDB
    print(f"\n🥑 Чтение ArangoDB")
    arango_companies = []
    arango_aliases = set()
    try:
        db = DBManager().get_arango_db()
        if db.has_collection('Companies'):
            # Получаем все документы
            cursor = db.collection('Companies').all()
            # Собираем имена и алиасы
            for doc in cursor:
                name = normalize_name(doc.get('name', ''))
                arango_companies.append(name)
                
                # Собираем все возможные имена (name, legal_name, aliases)
                arango_aliases.add(name)
                if 'legal_name' in doc:
                    arango_aliases.add(normalize_name(doc['legal_name']))
                if 'aliases' in doc and isinstance(doc['aliases'], list):
                    for alias in doc['aliases']:
                        arango_aliases.add(normalize_name(alias))
            
            print(f"   ✅ Найдено {len(arango_companies)} компаний в коллекции Companies")
        else:
            print("   ❌ Коллекция Companies не найдена!")
    except Exception as e:
        print(f"   ❌ Ошибка чтения ArangoDB: {e}")

    # 4. Сравнение
    print("\n" + "="*80)
    print("📊 Результаты сравнения (относительно Excel)")
    print("="*80)

    excel_set = set(excel_companies)
    duck_set = set(duckdb_companies)
    # arango_set = set(arango_companies) # Старая логика

    # DuckDB vs Excel
    missing_in_duck = excel_set - duck_set
    extra_in_duck = duck_set - excel_set

    if not missing_in_duck and not extra_in_duck:
        print("✅ DuckDB полностью совпадает с Excel")
    else:
        if missing_in_duck:
            print(f"❌ В DuckDB отсутствуют ({len(missing_in_duck)}):")
            for c in sorted(missing_in_duck):
                print(f"   - {c}")
        if extra_in_duck:
            print(f"⚠️  В DuckDB лишние ({len(extra_in_duck)}):")
            for c in sorted(extra_in_duck):
                print(f"   + {c}")

    print("-" * 40)

    # ArangoDB vs Excel (проверка через алиасы)
    missing_in_arango = []
    for company in excel_companies:
        if company not in arango_aliases:
            missing_in_arango.append(company)
    
    if not missing_in_arango:
        print("✅ Все компании из Excel присутствуют в ArangoDB (по имени или алиасам)")
    else:
        print(f"❌ В ArangoDB не найдены ({len(missing_in_arango)}):")
        for c in sorted(missing_in_arango):
            print(f"   - {c}")
            
    # Проверка флага is_group (если есть такая логика)
    # Пока просто проверяем наличие

if __name__ == "__main__":
    main()
