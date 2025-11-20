#!/usr/bin/env python3
"""
Импорт ОСВ по счетам затрат (20, 26, 44) в DuckDB.
Файлы содержат обороты по статьям затрат.
"""

import pandas as pd
import duckdb
from pathlib import Path
import os

# === Настройки ===
BASE_INPUT_FOLDER = Path("/opt/docagent/data/osv_revenue_0925/input")
DB_PATH = Path("/opt/docagent/knowledge_base/duckdb/osv/osv_database.duckdb")

def parse_osv_costs(file_path, account_type):
    print(f"📄 Обработка: {file_path.name}")
    
    try:
        # 1. Читаем заголовок для названия компании
        header_raw = pd.read_excel(file_path, header=None, nrows=10)
        company_name = header_raw.iloc[0, 0] if not pd.isna(header_raw.iloc[0, 0]) else ""
        # print(f"   Компания: {company_name}")
        
        # 2. Ищем строку с заголовками колонок
        header_row_idx = -1
        for idx, row in header_raw.iterrows():
            row_str = row.astype(str).str.lower().tolist()
            # Ищем ключевые слова заголовка: "Счет" и "Оборот Дт"
            if any("счет" in s for s in row_str) and any("оборот дт" in s for s in row_str):
                header_row_idx = idx
                break
        
        if header_row_idx == -1:
            print("   ❌ Не найден заголовок таблицы")
            return None
            
        # 3. Читаем данные
        df = pd.read_excel(file_path, header=header_row_idx)
        
        # Очищаем имена колонок
        df.columns = [str(c).strip().replace('\n', ' ') for c in df.columns]
        
        # 4. Определяем индексы ключевых колонок
        col_item_idx = 0 # Обычно первая колонка - статьи затрат
        col_turn_dt_idx = -1
        col_turn_kt_idx = -1
        
        for i, col in enumerate(df.columns):
            c_lower = col.lower()
            if "статьи затрат" in c_lower or "номенклатурные группы" in c_lower:
                 col_item_idx = i
            elif "оборот дт" in c_lower and "сальдо" not in c_lower:
                col_turn_dt_idx = i
            elif "оборот кт" in c_lower and "сальдо" not in c_lower:
                col_turn_kt_idx = i
                
        if col_turn_dt_idx == -1 or col_turn_kt_idx == -1:
            print(f"   ❌ Не найдены колонки оборотов")
            return None
            
        # 5. Извлекаем данные
        data_rows = []
        
        def clean_num(val):
            if pd.isna(val): return 0.0
            if isinstance(val, (int, float)): return float(val)
            try:
                return float(str(val).replace('\xa0', '').replace(' ', '').replace(',', '.'))
            except:
                return 0.0

        for _, row in df.iterrows():
            item_val = row.iloc[col_item_idx]
            if pd.isna(item_val):
                continue
            
            item_str = str(item_val).strip()
            
            # Фильтрация строк
            # 1. Пропускаем заголовок, если он попал
            if item_str.lower() in ['nan', 'итого', 'счет', 'статьи затрат']:
                continue
            # 2. Пропускаем номер счета (например "20")
            if item_str == account_type:
                continue
            # 3. Пропускаем "<...>" (это часто строка с общим итогом в 1С)
            if "<" in item_str and ">" in item_str:
                continue
                
            turn_dt = clean_num(row.iloc[col_turn_dt_idx])
            turn_kt = clean_num(row.iloc[col_turn_kt_idx])
            
            if turn_dt == 0 and turn_kt == 0:
                continue
                
            row_data = {
                'filename': file_path.name,
                'company_raw': company_name,
                'period': '9_months_2025',
                'account_type': account_type, # 20, 26, 44
                'cost_item': item_str,
                'amount_dt': turn_dt, # Начислено затрат
                'amount_kt': turn_kt  # Списано затрат
            }
            data_rows.append(row_data)
            
        return pd.DataFrame(data_rows)

    except Exception as e:
        print(f"   ❌ Ошибка: {e}")
        return None

def process_account(account_type, folder_name):
    print("="*80)
    print(f"🏭 Импорт ОСВ по счету {account_type} (Затраты)")
    print("="*80)
    
    input_folder = BASE_INPUT_FOLDER / folder_name
    # Внутри папки может быть подпапка с номером счета (например osv_20_9m/20)
    # Проверим, есть ли подпапка с именем счета
    if (input_folder / account_type).exists():
        input_folder = input_folder / account_type
    
    if not input_folder.exists():
        print(f"❌ Папка не найдена: {input_folder}")
        return
        
    files = sorted([f for f in input_folder.glob("*.xlsx") if not f.name.startswith("~$")])
    print(f"📂 Найдено файлов: {len(files)}")
    
    all_data = []
    for f in files:
        df = parse_osv_costs(f, account_type)
        if df is not None and not df.empty:
            all_data.append(df)
            # print(f"   ✅ Загружено строк: {len(df)}")
            
    if all_data:
        full_df = pd.concat(all_data, ignore_index=True)
        
        print(f"\n🦆 Сохранение {account_type} в DuckDB...")
        conn = duckdb.connect(str(DB_PATH))
        
        conn.execute("""
            CREATE TABLE IF NOT EXISTS osv_costs (
                filename VARCHAR,
                company_raw VARCHAR,
                period VARCHAR,
                account_type VARCHAR,
                cost_item VARCHAR,
                amount_dt DOUBLE,
                amount_kt DOUBLE
            )
        """)
        
        conn.execute(f"DELETE FROM osv_costs WHERE account_type = '{account_type}' AND period = '9_months_2025'")
        conn.execute("INSERT INTO osv_costs SELECT * FROM full_df")
        
        count = conn.execute(f"SELECT COUNT(*) FROM osv_costs WHERE account_type = '{account_type}'").fetchone()[0]
        print(f"✅ Всего записей по счету {account_type}: {count}")
        conn.close()
    else:
        print(f"⚠️  Нет данных для счета {account_type}")

def main():
    process_account("20", "osv_20_9m")
    process_account("26", "osv_26_9m")
    process_account("44", "osv_44_9m")

if __name__ == "__main__":
    main()
