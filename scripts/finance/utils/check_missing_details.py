import duckdb
import pandas as pd

DB_PATH = "/opt/docagent/knowledge_base/duckdb/osv/osv_database.duckdb"

def check_missing_data():
    conn = duckdb.connect(DB_PATH)
    
    print("🔍 Analyzing Data Availability for Consolidation...")
    
    # 1. Check existing detailed tables
    tables = [x[0] for x in conn.execute("SHOW TABLES").fetchall()]
    print(f"   Existing Tables: {tables}")
    
    has_60 = 'osv_60' in tables
    has_62 = 'osv_62' in tables
    has_66 = 'osv_66' in tables
    has_67 = 'osv_67' in tables
    has_76 = 'osv_76' in tables
    has_58 = 'osv_58' in tables
    
    # 2. Check Balances in General OSV to see importance
    print("\n📊 Significant Balances in General OSV (End of Period):")
    query = """
    SELECT 
        SUBSTR(account, 1, 2) as acc_group,
        SUM(end_dt) as total_asset,
        SUM(end_kt) as total_liab
    FROM osv_general
    WHERE acc_group IN ('60', '62', '66', '67', '76', '58')
    GROUP BY acc_group
    ORDER BY acc_group
    """
    balances = conn.execute(query).fetchdf()
    
    print(f"{'Account':<10} | {'Total Asset (Dt)':<20} | {'Total Liab (Kt)':<20} | {'Detailed Data?'}")
    print("-" * 70)
    
    for _, row in balances.iterrows():
        acc = row['acc_group']
        asset = row['total_asset']
        liab = row['total_liab']
        
        is_present = "✅ Yes"
        if acc == '60' and not has_60: is_present = "❌ MISSING"
        elif acc == '62' and not has_62: is_present = "❌ MISSING"
        elif acc == '66' and not has_66: is_present = "❌ MISSING"
        elif acc == '67' and not has_67: is_present = "❌ MISSING"
        elif acc == '76' and not has_76: is_present = "❌ MISSING"
        elif acc == '58' and not has_58: is_present = "❌ MISSING" # Financial investments
        elif acc not in ['60', '62', '66', '67', '76', '58']: is_present = "❓ N/A"
        
        # For 60, we have it. For others, likely missing.
        if acc == '60': is_present = "✅ Yes (osv_60)"
        else: is_present = "❌ MISSING"
        
        print(f"{acc:<10} | {asset:,.2f}".ljust(33) + f" | {liab:,.2f}".ljust(23) + f" | {is_present}")

    print("\n💡 CONCLUSION:")
    print("To perform accurate intercompany elimination (Step 4 & 5), we need detailed OSV files (with counterparties) for:")
    if not has_62: print("   - Account 62 (Buyers) -> To match against 60 and find revenue elimination.")
    if not has_66: print("   - Account 66 (Short-term Loans) -> To find intercompany loans.")
    if not has_67: print("   - Account 67 (Long-term Loans) -> To find intercompany loans.")
    if not has_76: print("   - Account 76 (Other Settlements) -> Often used for dividends/claims.")

if __name__ == "__main__":
    check_missing_data()
