import duckdb
import pandas as pd

DUCK_DB_PATH = '/opt/docagent/temp_osv.duckdb'
EXCEL_PATH = '/opt/docagent/data/osv_revenue_0925/output/consolidated_revenue.xlsx'

def compare_companies():
    # 1. Get DuckDB companies
    con = duckdb.connect(DUCK_DB_PATH)
    duck_companies = [r[0] for r in con.execute("SELECT DISTINCT company_name FROM osv_detailed").fetchall()]
    
    # 2. Get Excel companies
    df = pd.read_excel(EXCEL_PATH)
    excel_companies = [str(c).strip() for c in df['Компания'].dropna().unique() if str(c).strip().lower() != 'nan']
    
    # Normalize for comparison (simple lowercase check)
    duck_set = set(c.lower() for c in duck_companies)
    
    print(f"📊 DuckDB Companies ({len(duck_companies)}):")
    for c in duck_companies:
        print(f"  - {c}")
        
    print(f"\n📊 Excel Group Companies ({len(excel_companies)}):")
    missing = []
    matched = []
    
    # Manual mapping check based on our aliases
    aliases = {
        'гросс груп m': 'ггм',
        'гросс груп ди': 'ггди',
        'юг истейт инжиниринг': 'юг-истейт',
        'грандпром': 'грандпром',
        'сгк-регион': 'сгк-регион'
    }
    
    for exc in excel_companies:
        exc_lower = exc.lower()
        found = False
        
        # Direct match
        if exc_lower in duck_set:
            found = True
        
        # Alias match (reverse check)
        if not found:
            for duck_c in duck_companies:
                duck_lower = duck_c.lower()
                if aliases.get(duck_lower) == exc_lower or aliases.get(exc_lower) == duck_lower:
                    found = True
                    break
                    
        # Fuzzy match check (e.g. "ГГМ" vs "Гросс Груп М")
        if not found:
             if exc_lower == 'ггм' and 'гросс груп m' in duck_set: found = True
             if exc_lower == 'ггди' and 'гросс груп ди' in duck_set: found = True
             if exc_lower == 'юг-истейт' and 'юг истейт инжиниринг' in duck_set: found = True
        
        if found:
            matched.append(exc)
        else:
            missing.append(exc)
            
    print(f"\n❌ Missing in DuckDB ({len(missing)}):")
    for m in missing:
        print(f"  - {m}")

if __name__ == "__main__":
    compare_companies()
