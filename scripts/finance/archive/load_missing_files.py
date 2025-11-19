import pandas as pd
import duckdb
import os
import re

INPUT_DIR = '/opt/docagent/data/osv_revenue_0925/input'
DB_PATH = '/opt/docagent/temp_osv.duckdb'

def normalize_float(val):
    if pd.isna(val):
        return 0.0
    if isinstance(val, str):
        val = val.replace(',', '.').replace(' ', '')
        try:
            return float(val)
        except:
            return 0.0
    return float(val)

def parse_and_load():
    con = duckdb.connect(DB_PATH)
    
    # Get existing files to avoid duplicates
    existing_files = set()
    try:
        res = con.execute("SELECT DISTINCT source_file FROM osv_detailed").fetchall()
        existing_files = {r[0] for r in res}
    except:
        pass
        
    print(f"Found {len(existing_files)} already loaded files.")
    
    files = [f for f in os.listdir(INPUT_DIR) if f.endswith('.xlsx') and 'Группа' not in f]
    
    for filename in files:
        if filename in existing_files:
            print(f"Skipping {filename} (already loaded)")
            continue
            
        filepath = os.path.join(INPUT_DIR, filename)
        print(f"Processing {filename}...")
        
        try:
            # Read file
            df = pd.read_excel(filepath, header=None)
            
            # Find header row
            header_row_idx = None
            for idx, row in df.iterrows():
                row_str = ' '.join([str(x) for x in row.values])
                # print(f"Row {idx}: {row_str}") # Debug
                if ('Контрагент' in row_str or '62' in row_str) and ('Сальдо' in row_str or 'сальдо' in row_str):
                    header_row_idx = idx
                    break
            
            if header_row_idx is None:
                # Try simpler check
                for idx, row in df.iterrows():
                    row_str = ' '.join([str(x) for x in row.values])
                    if 'Начальное сальдо' in row_str:
                        header_row_idx = idx
                        break
            
            if header_row_idx is None:
                print(f"⚠️ Could not find header row in {filename}")
                continue
            
            # ... (Company extraction logic remains same) ...
            
            # Set headers and strip spaces
            df.columns = [str(c).strip() for c in df.iloc[header_row_idx]]
            df = df.iloc[header_row_idx+1:]
            
            # Identify columns
            cols = list(df.columns)
            
            col_subkonto = None
            # ...
            
            for i, c in enumerate(cols):
                c_lower = c.lower()
                if 'контрагент' in c_lower: col_subkonto = c
                elif c == '62': col_subkonto = c # Special case for VFTs
                elif 'начальное' in c_lower and 'дт' in c_lower: col_op_dt = c
                elif 'начальное' in c_lower and 'кт' in c_lower: col_op_kt = c
                elif 'конечное' in c_lower and 'дт' in c_lower: col_cl_dt = c
                elif 'конечное' in c_lower and 'кт' in c_lower: col_cl_kt = c
                elif 'оборот' in c_lower:
                    # Determine if Debit or Credit turnover for Account 62
                    # Dt62 ... -> Debit Turnover
                    # ... Kt62 -> Credit Turnover
                    if 'д' in c_lower and ('62' in c_lower or 'дт62' in c_lower) and 'к' in c_lower:
                        # Check order. "Дт62 К90" -> Debit 62. "Д51 Кт 62" -> Credit 62.
                        if 'дт62' in c_lower or 'д62' in c_lower:
                             # Likely Debit Turnover
                             cols_turn_dt.append(c)
                        elif 'кт62' in c_lower or 'к62' in c_lower:
                             # Likely Credit Turnover
                             cols_turn_kt.append(c)
            
            # Fallback for subkonto
            if not col_subkonto:
                col_subkonto = cols[0] # Assume first column
            
            # Prepare data for insertion
            data_to_insert = []
            for _, row in df.iterrows():
                subkonto = str(row[col_subkonto]) if col_subkonto and pd.notna(row[col_subkonto]) else None
                if not subkonto or subkonto.lower() == 'nan' or 'итого' in subkonto.lower():
                    continue
                    
                op_dt = normalize_float(row[col_op_dt]) if col_op_dt else 0.0
                op_kt = normalize_float(row[col_op_kt]) if col_op_kt else 0.0
                cl_dt = normalize_float(row[col_cl_dt]) if col_cl_dt else 0.0
                cl_kt = normalize_float(row[col_cl_kt]) if col_cl_kt else 0.0
                
                turn_dt = sum(normalize_float(row[c]) for c in cols_turn_dt)
                turn_kt = sum(normalize_float(row[c]) for c in cols_turn_kt)
                
                # Skip empty rows
                if op_dt == 0 and op_kt == 0 and turn_dt == 0 and turn_kt == 0 and cl_dt == 0 and cl_kt == 0:
                    continue
                
                data_to_insert.append((
                    company_name,
                    None, # inn
                    '9 months 2025', # period
                    '62', # account
                    subkonto,
                    op_dt,
                    op_kt,
                    turn_dt,
                    turn_kt,
                    cl_dt,
                    cl_kt,
                    filename,
                    '2025-11-19' # import_date
                ))
            
            if data_to_insert:
                print(f"   Inserting {len(data_to_insert)} rows...")
                con.executemany("""
                    INSERT INTO osv_detailed (
                        company_name, inn, period, account, subkonto, 
                        opening_debit, opening_credit, turnover_debit, turnover_credit, 
                        closing_debit, closing_credit, source_file, import_date
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, data_to_insert)
                print("   ✅ Done.")
            else:
                print("   ⚠️ No data found to insert.")
                
        except Exception as e:
            print(f"❌ Error processing {filename}: {e}")

if __name__ == "__main__":
    parse_and_load()
