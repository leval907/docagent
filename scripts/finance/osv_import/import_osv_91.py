#!/usr/bin/env python3
"""
Импорт ОСВ по счету 91 (Прочие доходы и расходы) в DuckDB.
Учитывает иерархию: 91 -> 91.01/91.02 -> Статьи.
"""

import pandas as pd
import duckdb
from pathlib import Path
import os
import re

# === Настройки ===
INPUT_FOLDER = Path("/opt/docagent/data/osv_revenue_0925/input/osv_91_9m/91")
DB_PATH = Path("/opt/docagent/knowledge_base/duckdb/osv/osv_database.duckdb")
ACCOUNT_TYPE = "91"

def parse_osv_91(file_path):
    print(f"📄 Обработка: {file_path.name}")
    
    try:
        # 1. Читаем заголовок для названия компании
        header_raw = pd.read_excel(file_path, header=None, nrows=15)
        company_name = header_raw.iloc[0, 0] if not pd.isna(header_raw.iloc[0, 0]) else ""
        
        # 2. Ищем строку с заголовками колонок
        header_row_idx = -1
        for idx, row in header_raw.iterrows():
            row_str = row.astype(str).str.lower().tolist()
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
        col_item_idx = 0 
        col_turn_dt_idx = -1
        col_turn_kt_idx = -1
        
        for i, col in enumerate(df.columns):
            c_lower = col.lower()
            if "счет" in c_lower or "прочие доходы" in c_lower: # Первая колонка
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
        current_subaccount = None # 91.01, 91.02, 91.09
        
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
            item_lower = item_str.lower()
            
            # Пропускаем мусор
            if item_lower in ['nan', 'итого', 'счет']:
                continue
                
            # Определение субсчета
            if item_str.startswith("91."):
                current_subaccount = item_str
                continue # Это строка-заголовок субсчета, пропускаем её, чтобы не дублировать
            
            # Пропускаем общий итог "91"
            if item_str == "91":
                continue
                
            # Если мы не внутри субсчета, и это не заголовок, то странно, но бывает
            # Обычно сначала идет 91, потом 91.01
            
            turn_dt = clean_num(row.iloc[col_turn_dt_idx])
            turn_kt = clean_num(row.iloc[col_turn_kt_idx])
            
            if turn_dt == 0 and turn_kt == 0:
                continue
                
            row_data = {
                'filename': file_path.name,
                'company_raw': company_name,
                'period': '9_months_2025',
                'account_type': '91',
                'subaccount': current_subaccount, # 91.01 (Доходы), 91.02 (Расходы)
                'item_name': item_str,
                'amount_dt': turn_dt,
                'amount_kt': turn_kt
            }
            data_rows.append(row_data)
            
        return pd.DataFrame(data_rows)

    except Exception as e:
        print(f"   ❌ Ошибка: {e}")
        return None

def main():
    print("="*80)
    print(f"🏭 Импорт ОСВ по счету 91 (Прочие доходы и расходы)")
    print("="*80)
    
    if not INPUT_FOLDER.exists():
        print(f"❌ Папка не найдена: {INPUT_FOLDER}")
        return
        
    files = sorted([f for f in INPUT_FOLDER.glob("*.xlsx") if not f.name.startswith("~$")])
    print(f"📂 Найдено файлов: {len(files)}")
    
    all_data = []
    for f in files:
        df = parse_osv_91(f)
        if df is not None and not df.empty:
            all_data.append(df)
            
    if all_data:
        full_df = pd.concat(all_data, ignore_index=True)
        
        print("\n🦆 Сохранение в DuckDB...")
        conn = duckdb.connect(str(DB_PATH))
        
        conn.execute("""
            CREATE TABLE IF NOT EXISTS osv_91 (
                filename VARCHAR,
                company_raw VARCHAR,
                period VARCHAR,
                account_type VARCHAR,
                subaccount VARCHAR,
                item_name VARCHAR,
                amount_dt DOUBLE,
                amount_kt DOUBLE
            )
        """)
        
        conn.execute(f"DELETE FROM osv_91 WHERE period = '9_months_2025'")
        conn.execute("INSERT INTO osv_91 SELECT * FROM full_df")
        
        count = conn.execute(f"SELECT COUNT(*) FROM osv_91").fetchone()[0]
        print(f"✅ Всего записей по счету 91: {count}")
        
        print("\n📊 Итоги по субсчетам:")
        res = conn.execute("""
            SELECT subaccount, SUM(amount_dt) as Dt, SUM(amount_kt) as Kt 
            FROM osv_91 
            GROUP BY subaccount
        """).fetchdf()
        print(res)
        
        conn.close()
    else:
        print("⚠️  Нет данных для сохранения")

if __name__ == "__main__":
    main()
