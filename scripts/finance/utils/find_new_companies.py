import duckdb
import pandas as pd

DB_PATH = "/opt/docagent/knowledge_base/duckdb/osv/osv_database.duckdb"

def find_diff():
    conn = duckdb.connect(DB_PATH)
    
    # Get companies from osv_general (the 25 files)
    general_companies = conn.execute("SELECT DISTINCT company_raw FROM osv_general").fetchdf()['company_raw'].tolist()
    
    # Get companies from group_companies (the 23 known ones)
    # Note: group_companies names might be slightly different (normalized vs raw)
    # Let's fetch them and try to match
    group_companies = conn.execute("SELECT company_name FROM group_companies").fetchdf()['company_name'].tolist()
    
    conn.close()
    
    print("Companies in OSV General (25):")
    for c in sorted(general_companies):
        print(f"  {c}")
        
    print("\nCompanies in Group List (23):")
    for c in sorted(group_companies):
        print(f"  {c}")
        
    # Simple set difference won't work perfectly due to naming differences (e.g. "ООО АЛЬЯНС" vs "АЛЬЯНС ООО")
    # But let's try to spot the obvious ones
    
if __name__ == "__main__":
    find_diff()
