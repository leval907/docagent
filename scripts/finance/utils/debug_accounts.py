import pandas as pd
import re

def analyze_accounts():
    file_path = '/opt/docagent/docs/a-findocs/План счетов.xlsx'
    df = pd.read_excel(file_path, dtype=str)
    print(f"Total rows in Excel: {len(df)}")
    
    valid_codes = []
    skipped = []
    duplicates = []
    seen_codes = set()
    
    for idx, row in df.iterrows():
        raw_code = str(row['Код счета']).strip()
        # Logic from loader
        code = re.sub(r'[^0-9.]', '', raw_code)
        
        if not code:
            skipped.append(f"Row {idx}: Empty code (Raw: {raw_code})")
            continue
            
        if code in seen_codes:
            duplicates.append(code)
        else:
            seen_codes.add(code)
            valid_codes.append(code)
            
    print(f"Valid unique codes: {len(valid_codes)}")
    print(f"Skipped rows: {len(skipped)}")
    print(f"Duplicate codes found: {len(duplicates)}")
    
    if duplicates:
        print(f"Sample duplicates: {duplicates[:5]}")
    if skipped:
        print(f"Sample skipped: {skipped[:5]}")

if __name__ == "__main__":
    analyze_accounts()
