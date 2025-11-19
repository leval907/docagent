import duckdb
import os

DB_PATH = '/opt/docagent/temp_osv.duckdb'

def inspect_duckdb():
    if not os.path.exists(DB_PATH):
        print(f"❌ Database file not found at: {DB_PATH}")
        # Try to find it
        for root, dirs, files in os.walk('/opt'):
            if 'osv_database.duckdb' in files:
                print(f"Found at: {os.path.join(root, 'osv_database.duckdb')}")
        return

    print(f"📂 Connecting to DuckDB: {DB_PATH}")
    try:
        con = duckdb.connect(DB_PATH)
        
        # List tables
        tables = con.execute("SHOW TABLES").fetchall()
        print(f"Found {len(tables)} tables:")
        for t in tables:
            print(f" - {t[0]}")
            
        # Try to find companies
        # Common names for company tables: companies, organizations, mapping, etc.
        potential_tables = [t[0] for t in tables]
        
        for table in potential_tables:
            if 'company' in table.lower() or 'org' in table.lower() or 'mapping' in table.lower() or 'group' in table.lower():
                print(f"\n🔎 Inspecting table: {table}")
                columns = con.execute(f"DESCRIBE {table}").fetchall()
                col_names = [c[0] for c in columns]
                print(f"   Columns: {col_names}")
                
                count = con.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
                print(f"   Row count: {count}")
                
                if count > 0:
                    print("   Sample data:")
                    sample = con.execute(f"SELECT * FROM {table} LIMIT 5").fetchall()
                    for row in sample:
                        print(f"   {row}")

    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    inspect_duckdb()
