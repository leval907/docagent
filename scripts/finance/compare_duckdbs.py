import duckdb
import os

DB_PATHS = [
    '/opt/1_Project_Alayns/osv-consolidation/osv_database.duckdb',
    '/opt/docagent/knowledge_base/duckdb/analytics.duckdb',
    '/opt/docagent/knowledge_base/duckdb/osv/osv_database.duckdb'
]

def check_db(path):
    print(f"\n{'='*50}")
    print(f"Checking: {path}")
    print(f"{'='*50}")
    
    if not os.path.exists(path):
        print("File not found.")
        return

    try:
        con = duckdb.connect(path, read_only=True)
        
        print("Tables:")
        tables = con.execute("SHOW TABLES").fetchall()
        if not tables:
            print("  (No tables found)")
        for t in tables:
            print(f"  - {t[0]}")
            
            # Get row count for each table
            try:
                count = con.execute(f"SELECT COUNT(*) FROM {t[0]}").fetchone()[0]
                print(f"    Rows: {count}")
            except:
                pass

        con.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    for p in DB_PATHS:
        check_db(p)
