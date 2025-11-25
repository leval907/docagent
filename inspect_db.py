import duckdb
import pandas as pd

db_path = '/opt/1_Project_Alayns/osv-consolidation/osv_database.duckdb'

try:
    con = duckdb.connect(db_path)
    
    print("Tables:")
    tables = con.execute("SHOW TABLES").fetchall()
    for t in tables:
        print(t[0])
        
    # Check if history.osv_9m_summary exists (it might be just osv_9m_summary or in a schema)
    # The dbt model referred to source('history', 'osv_9m_summary')
    
    print("\nChecking for 'osv_9m_summary' or similar...")
    
    # Try to find the table name that matches
    table_name = None
    for t in tables:
        if 'osv_9m_summary' in t[0]:
            table_name = t[0]
            break
            
    if table_name:
        print(f"\nAnalyzing table: {table_name}")
        
        # Check account codes
        print("\nDistinct Account Codes (first 20):")
        accounts = con.execute(f"SELECT DISTINCT account_code FROM {table_name} ORDER BY account_code LIMIT 20").fetchall()
        for a in accounts:
            print(a[0])
            
        # Check for specific asset accounts
        asset_accounts = ['01', '02', '03', '08']
        print(f"\nChecking for asset accounts {asset_accounts}:")
        for acc in asset_accounts:
            count = con.execute(f"SELECT COUNT(*) FROM {table_name} WHERE account_code LIKE '{acc}%'").fetchone()[0]
            print(f"Account {acc}: {count} records")

        # Check analytic types
        print("\nDistinct Analytic 1 Types:")
        analytics = con.execute(f"SELECT DISTINCT analytic_1_type FROM {table_name} LIMIT 20").fetchall()
        for a in analytics:
            print(a[0])
            
    else:
        print("\nTable 'osv_9m_summary' not found in the default schema. Checking schemas...")
        schemas = con.execute("SELECT schema_name FROM information_schema.schemata").fetchall()
        print("Schemas:", [s[0] for s in schemas])
        
        # If history schema exists, check tables there
        if 'history' in [s[0] for s in schemas]:
             tables_hist = con.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'history'").fetchall()
             print("\nTables in 'history' schema:", [t[0] for t in tables_hist])

except Exception as e:
    print(f"Error: {e}")
