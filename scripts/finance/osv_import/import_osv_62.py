#!/usr/bin/env python3
"""
Import OSV for Account 62 (Buyers) into DuckDB.
Structure: 62 -> 62.01/62.02 -> Counterparties.
"""

import pandas as pd
import duckdb
from pathlib import Path
import os
import re

# === Settings ===
INPUT_FOLDER = Path("/opt/1_Project_Alayns/files")
DB_PATH = Path("/opt/docagent/knowledge_base/duckdb/osv/osv_database.duckdb")
ACCOUNT_TYPE = "62"

def parse_osv_62(file_path):
    print(f"📄 Processing: {file_path.name}")
    
    try:
        # 1. Read header to detect format
        header_raw = pd.read_excel(file_path, header=None, nrows=20)
        
        is_english_format = False
        header_row_idx = -1
        
        # Check for English SQL Export format (Header usually at row 0)
        row0_str = header_raw.iloc[0].astype(str).str.lower().tolist()
        if "company_name" in row0_str and "subkonto" in row0_str:
            is_english_format = True
            header_row_idx = 0
            company_name = "FromColumn" # Will be extracted from data
        else:
            # 1C Format
            company_name = header_raw.iloc[0, 0] if not pd.isna(header_raw.iloc[0, 0]) else "Unknown"
            
            for idx, row in header_raw.iterrows():
                row_str = row.astype(str).str.lower().tolist()
                if "контрагенты" in row_str:
                    header_row_idx = idx
                    break
        
        if header_row_idx == -1:
            print("   ❌ Header row not found")
            return None
            
        # 3. Read data
        df = pd.read_excel(file_path, header=header_row_idx)
        
        # Clean column names
        df.columns = [str(c).strip().replace('\n', ' ') for c in df.columns]
        
        # 4. Identify columns
        col_item_idx = -1 
        col_init_dt_idx = -1
        col_init_kt_idx = -1
        col_turn_dt_idx = -1
        col_turn_kt_idx = -1
        col_final_dt_idx = -1
        col_final_kt_idx = -1
        col_company_idx = -1 # For English format
        
        if is_english_format:
            # Map English columns
            for i, col in enumerate(df.columns):
                c_lower = col.lower()
                if "subkonto" in c_lower or "counterparty" in c_lower: col_item_idx = i
                elif "opening_debit" in c_lower: col_init_dt_idx = i
                elif "opening_credit" in c_lower: col_init_kt_idx = i
                elif "turnover_debit" in c_lower: col_turn_dt_idx = i
                elif "turnover_credit" in c_lower: col_turn_kt_idx = i
                elif "closing_debit" in c_lower: col_final_dt_idx = i
                elif "closing_credit" in c_lower: col_final_kt_idx = i
                elif "company_name" in c_lower: col_company_idx = i
        else:
            # Map Russian columns (1C Standard)
            for i, col in enumerate(df.columns):
                if "контрагенты" in col.lower():
                    col_item_idx = i
                    col_init_dt_idx = i + 1
                    col_init_kt_idx = i + 2
                    col_turn_dt_idx = i + 3
                    col_turn_kt_idx = i + 4
                    col_final_dt_idx = i + 5
                    col_final_kt_idx = i + 6
                    break
                
        if col_item_idx == -1:
             print(f"   ❌ Item column not found")
             return None

        # 5. Extract data
        data_rows = []
        current_subaccount = "62" # Default root
        
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
            
            # Skip garbage
            if item_lower in ['nan', 'итого', 'счет', 'контрагенты', 'субконто']:
                continue
            
            # Determine Company Name for this row
            if is_english_format and col_company_idx != -1:
                row_company = str(row.iloc[col_company_idx]).strip()
            else:
                row_company = company_name

            # Detect subaccount (62.01, 62.02)
            if item_str.startswith("62."):
                current_subaccount = item_str
                continue 
            
            # Skip total "62"
            if item_str == "62":
                continue
                
            # Extract values
            init_dt = clean_num(row.iloc[col_init_dt_idx]) if col_init_dt_idx != -1 else 0.0
            init_kt = clean_num(row.iloc[col_init_kt_idx]) if col_init_kt_idx != -1 else 0.0
            turn_dt = clean_num(row.iloc[col_turn_dt_idx])
            turn_kt = clean_num(row.iloc[col_turn_kt_idx])
            final_dt = clean_num(row.iloc[col_final_dt_idx]) if col_final_dt_idx != -1 else 0.0
            final_kt = clean_num(row.iloc[col_final_kt_idx]) if col_final_kt_idx != -1 else 0.0
            
            # Skip if all zeros
            if all(v == 0 for v in [init_dt, init_kt, turn_dt, turn_kt, final_dt, final_kt]):
                continue
                
            row_data = {
                'filename': file_path.name,
                'company_raw': row_company,
                'period': '9_months_2025',
                'account_type': '62',
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
        print(f"   ❌ Error: {e}")
        return None

def main():
    print("="*80)
    print(f"🏭 Import OSV for Account 62 (Buyers)")
    print("="*80)
    
    if not INPUT_FOLDER.exists():
        print(f"❌ Folder not found: {INPUT_FOLDER}")
        return
        
    # Find all files with '62' in the name, recursively
    files = sorted([f for f in INPUT_FOLDER.rglob("*62*.xls*") if not f.name.startswith("~$")])
    print(f"📂 Found files: {len(files)}")
    for f in files:
        print(f"   - {f.name}")
    
    all_data = []
    for f in files:
        df = parse_osv_62(f)
        if df is not None and not df.empty:
            all_data.append(df)
            
    if all_data:
        full_df = pd.concat(all_data, ignore_index=True)
        
        print("\n🦆 Saving to DuckDB...")
        conn = duckdb.connect(str(DB_PATH))
        
        conn.execute("""
            CREATE TABLE IF NOT EXISTS osv_62 (
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
        
        # Clear old data for this period
        conn.execute(f"DELETE FROM osv_62 WHERE period = '9_months_2025'")
        conn.execute("INSERT INTO osv_62 SELECT * FROM full_df")
        
        count = conn.execute(f"SELECT COUNT(*) FROM osv_62").fetchone()[0]
        print(f"✅ Total records for Account 62: {count}")
        
        print("\n📊 Top 5 Buyers by Turnover (Debit - Revenue):")
        res = conn.execute("""
            SELECT counterparty, SUM(turnover_dt) as total_revenue 
            FROM osv_62 
            GROUP BY counterparty 
            ORDER BY total_revenue DESC 
            LIMIT 5
        """).fetchdf()
        print(res)
        
        conn.close()
    else:
        print("⚠️  No data to save")

if __name__ == "__main__":
    main()
