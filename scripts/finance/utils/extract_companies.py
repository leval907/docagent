import duckdb

DB_PATH = '/opt/docagent/temp_osv.duckdb'

def extract_companies():
    con = duckdb.connect(DB_PATH)
    
    # Get unique companies from osv_detailed or summary
    # Let's check osv_detailed columns first to be sure
    cols = con.execute("DESCRIBE osv_detailed").fetchall()
    col_names = [c[0] for c in cols]
    
    if 'company_name' in col_names:
        companies = con.execute("SELECT DISTINCT company_name FROM osv_detailed ORDER BY company_name").fetchall()
        print(f"Found {len(companies)} companies in osv_detailed:")
        for c in companies:
            print(f" - {c[0]}")
            
        # Also check if there is a filename mapping
        if 'source_file' in col_names:
             mapping = con.execute("SELECT DISTINCT company_name, source_file FROM osv_detailed").fetchall()
             print("\nFile mapping:")
             for m in mapping:
                 print(f" - {m[0]} -> {m[1]}")
    else:
        print("Column 'organization' not found in osv_detailed")
        print(f"Columns: {col_names}")

if __name__ == "__main__":
    extract_companies()
