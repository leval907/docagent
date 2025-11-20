#!/usr/bin/env python3
"""
Импорт ОСВ по счету 60 (Расчеты с поставщиками) в DuckDB.
Структура: 60 -> 60.01/60.02 -> Контрагенты.
"""

import pandas as pd
import duckdb
from pathlib import Path
import os
import re

# === Настройки ===
INPUT_FOLDER = Path("/opt/docagent/data/osv_revenue_0925/input/osv_60_9m/60")
DB_PATH = Path("/opt/docagent/knowledge_base/duckdb/osv/osv_database.duckdb")
ACCOUNT_TYPE = "60"

def parse_osv_60(file_path):
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
        col_init_dt_idx = -1
        col_init_kt_idx = -1
        col_turn_dt_idx = -1
        col_turn_kt_idx = -1
        col_final_dt_idx = -1
        col_final_kt_idx = -1
        
        for i, col in enumerate(df.columns):
            c_lower = col.lower()
            if "счет" in c_lower or "контрагенты" in c_lower:
                 col_item_idx = i
            elif "начальное сальдо дт" in c_lower:
                col_init_dt_idx = i
            elif "начальное сальдо кт" in c_lower:
                col_init_kt_idx = i
            elif "оборот дт" in c_lower and "сальдо" not in c_lower:
                col_turn_dt_idx = i
            elif "оборот кт" in c_lower and "сальдо" not in c_lower:
                col_turn_kt_idx = i
            elif "конечное сальдо дт" in c_lower:
                col_final_dt_idx = i
            elif "конечное сальдо кт" in c_lower:
                col_final_kt_idx = i
                
        if col_turn_dt_idx == -1 or col_turn_kt_idx == -1:
            print(f"   ❌ Не найдены колонки оборотов")
            return None
            
        # 5. Извлекаем данные
        data_rows = []
        current_subaccount = "60" # Default root
        
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
            if item_lower in ['nan', 'итого', 'счет', 'контрагенты']:
                continue
                
            # Определение субсчета (60.01, 60.02)
            if item_str.startswith("60."):
                current_subaccount = item_str
                continue # Это заголовок субсчета
            
            # Пропускаем общий итог "60"
            if item_str == "60":
                continue
                
            # Извлекаем значения
            init_dt = clean_num(row.iloc[col_init_dt_idx]) if col_init_dt_idx != -1 else 0.0
            init_kt = clean_num(row.iloc[col_init_kt_idx]) if col_init_kt_idx != -1 else 0.0
            turn_dt = clean_num(row.iloc[col_turn_dt_idx])
            turn_kt = clean_num(row.iloc[col_turn_kt_idx])
            final_dt = clean_num(row.iloc[col_final_dt_idx]) if col_final_dt_idx != -1 else 0.0
            final_kt = clean_num(row.iloc[col_final_kt_idx]) if col_final_kt_idx != -1 else 0.0
            
            # Если все нули - пропускаем
            if all(v == 0 for v in [init_dt, init_kt, turn_dt, turn_kt, final_dt, final_kt]):
                continue
                
            row_data = {
                'filename': file_path.name,
                'company_raw': company_name,
                'period': '9_months_2025',
                'account_type': '60',
                'subaccount': current_subaccount,
                'counterparty': item_str,
                'initial_balance_dt': init_dt,
                'initial_balance_kt': init_kt,
                'turnover_dt': turn_dt,
                'turnover_kt': turn_kt,
                'final_balance_dt': final_dt,
                'final_balance_kt': final_kt
            }
            data_rows.append(row_data)
            
        return pd.DataFrame(data_rows)

    except Exception as e:
        print(f"   ❌ Ошибка: {e}")
        return None

def main():
    print("="*80)
    print(f"🏭 Импорт ОСВ по счету 60 (Поставщики)")
    print("="*80)
    
    if not INPUT_FOLDER.exists():
        print(f"❌ Папка не найдена: {INPUT_FOLDER}")
        return
        
    files = sorted([f for f in INPUT_FOLDER.glob("*.xlsx") if not f.name.startswith("~$")])
    print(f"📂 Найдено файлов: {len(files)}")
    
    all_data = []
    for f in files:
        df = parse_osv_60(f)
        if df is not None and not df.empty:
            all_data.append(df)
            
    if all_data:
        full_df = pd.concat(all_data, ignore_index=True)
        
        print("\n🦆 Сохранение в DuckDB...")
        conn = duckdb.connect(str(DB_PATH))
        
        conn.execute("""
            CREATE TABLE IF NOT EXISTS osv_60 (
                filename VARCHAR,
                company_raw VARCHAR,
                period VARCHAR,
                account_type VARCHAR,
                subaccount VARCHAR,
                counterparty VARCHAR,
                initial_balance_dt DOUBLE,
                initial_balance_kt DOUBLE,
                turnover_dt DOUBLE,
                turnover_kt DOUBLE,
                final_balance_dt DOUBLE,
                final_balance_kt DOUBLE
            )
        """)
        
        conn.execute(f"DELETE FROM osv_60 WHERE period = '9_months_2025'")
        conn.execute("INSERT INTO osv_60 SELECT * FROM full_df")
        
        count = conn.execute(f"SELECT COUNT(*) FROM osv_60").fetchone()[0]
        print(f"✅ Всего записей по счету 60: {count}")
        
        print("\n📊 Топ-5 Поставщиков по обороту (Кредит - Начислено):")
        res = conn.execute("""
            SELECT counterparty, SUM(turnover_kt) as total_invoiced 
            FROM osv_60 
            GROUP BY counterparty 
            ORDER BY total_invoiced DESC 
            LIMIT 5
        """).fetchdf()
        print(res)
        
        conn.close()
    else:
        print("⚠️  Нет данных для сохранения")

if __name__ == "__main__":
    main()
