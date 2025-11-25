
import duckdb
import pandas as pd

db_path = '/opt/1_Project_Alayns/osv-consolidation/osv_database.duckdb'

try:
    con = duckdb.connect(db_path)
    
    # Check schemas
    print("Schemas:")
    print(con.execute("SELECT schema_name FROM information_schema.schemata").df())
    
    # Check tables in history schema
    print("\nTables in history schema:")
    print(con.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'history'").df())
    
    # Check columns in history.osv_9m_summary
    print("\nColumns in history.osv_9m_summary:")
    print(con.execute("SELECT column_name, data_type FROM information_schema.columns WHERE table_schema = 'history' AND table_name = 'osv_9m_summary'").df())
    
    # Preview data
    print("\nPreview of history.osv_9m_summary:")
    print(con.execute("SELECT * FROM history.osv_9m_summary LIMIT 5").df())
    
    con.close()
except Exception as e:
    print(f"Error: {e}")
