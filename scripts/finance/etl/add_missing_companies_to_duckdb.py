import duckdb
import pandas as pd

DB_PATH = "/opt/docagent/knowledge_base/duckdb/osv/osv_database.duckdb"

def add_missing_companies():
    conn = duckdb.connect(DB_PATH)
    
    new_companies = ["ЗОРГ ООО", "ИНВЕСТ-СТРОЙ ООО"]
    
    print(f"Adding {len(new_companies)} companies to DuckDB group_companies table...")
    
    for company in new_companies:
        # Check if exists
        count = conn.execute("SELECT COUNT(*) FROM group_companies WHERE company_name = ?", [company]).fetchone()[0]
        if count == 0:
            conn.execute("INSERT INTO group_companies (company_name) VALUES (?)", [company])
            print(f"  ✅ Added: {company}")
        else:
            print(f"  ⚠️  Already exists: {company}")
            
    # Verify total count
    total = conn.execute("SELECT COUNT(*) FROM group_companies").fetchone()[0]
    print(f"Total companies in DuckDB: {total}")
    
    conn.close()

if __name__ == "__main__":
    add_missing_companies()
