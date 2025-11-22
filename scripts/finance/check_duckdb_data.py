import duckdb
import os

DB_PATH = '/opt/docagent/knowledge_base/duckdb/osv/osv_database.duckdb'

def check_data():
    if not os.path.exists(DB_PATH):
        print(f"Database not found at {DB_PATH}")
        return

    con = duckdb.connect(DB_PATH, read_only=True)
    
    print("Tables:")
    tables = con.execute("SHOW TABLES").fetchall()
    for t in tables:
        print(f"- {t[0]}")
        
    # Inspect specific tables
    for table in ['osv_51', 'osv_60', 'osv_62', 'group_companies']:
        print(f"\nSchema of {table}:")
        try:
            schema = con.execute(f"DESCRIBE {table}").fetchall()
            for col in schema:
                print(f"- {col[0]} ({col[1]})")
            
            print(f"Sample data from {table}:")
            sample = con.execute(f"SELECT * FROM {table} LIMIT 3").fetchall()
            for row in sample:
                print(row)
        except Exception as e:
            print(f"Error reading {table}: {e}")
            
    con.close()
        
    con.close()

if __name__ == "__main__":
    check_data()
