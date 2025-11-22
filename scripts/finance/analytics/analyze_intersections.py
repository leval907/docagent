import duckdb
import pandas as pd

DB_PATH = "/opt/docagent/knowledge_base/duckdb/osv/osv_database.duckdb"

def analyze_intersections():
    conn = duckdb.connect(DB_PATH)
    
    print("🔍 Analyzing Intersections between Account 60 (Suppliers) and 62 (Buyers)...")
    
    # 1. Get list of group companies to filter counterparties
    # We can use the 'group_companies' table if it exists, or just fuzzy match
    # For now, let's just look for exact name matches in counterparties
    
    query = """
    WITH buyers AS (
        SELECT DISTINCT counterparty as name FROM osv_62
    ),
    suppliers AS (
        SELECT DISTINCT counterparty as name FROM osv_60
    )
    SELECT 
        b.name as counterparty
    FROM buyers b
    JOIN suppliers s ON b.name = s.name
    ORDER BY b.name
    """
    
    intersections = conn.execute(query).fetchdf()
    
    print(f"✅ Found {len(intersections)} counterparties present in both 60 and 62.")
    print("   (These are potential candidates for elimination if they are Group Companies)")
    print("-" * 60)
    print(intersections.head(20).to_string(index=False))
    
    # 2. Calculate potential elimination amount
    # Sum of Min(Turnover 60 Kt, Turnover 62 Dt) for these intersections?
    # Actually, elimination is usually:
    # - Revenue (62 Dt) vs Cost (60 Kt) ? No.
    # - AR (62 Dt Balance) vs AP (60 Kt Balance) -> Balance Sheet Elimination
    # - Revenue (90.01) vs Cost (20/26/44 -> 90.02) -> P&L Elimination.
    # But here we are looking at 60 vs 62.
    # If Company A sells to Company B:
    # A has 62 Dt (Receivable from B) and 90.01 Kt (Revenue).
    # B has 60 Kt (Payable to A) and 10/20/41 Dt (Cost/Asset).
    
    # So we match A's 62 Dt Turnover with B's 60 Kt Turnover?
    # Or A's 62 Dt Balance with B's 60 Kt Balance?
    
    print("\n📊 Potential Balance Sheet Elimination (Receivables vs Payables):")
    
    # We need to know which counterparty maps to which internal company.
    # This is the hard part without a mapping table.
    # But we can list the amounts for the intersections.
    
    query_amounts = """
    SELECT 
        t62.counterparty,
        SUM(t62.final_balance_dt) as ar_balance_62,
        SUM(t60.final_balance_kt) as ap_balance_60
    FROM osv_62 t62
    JOIN osv_60 t60 ON t62.counterparty = t60.counterparty
    GROUP BY t62.counterparty
    HAVING ar_balance_62 > 0 OR ap_balance_60 > 0
    ORDER BY ar_balance_62 DESC
    LIMIT 20
    """
    
    amounts = conn.execute(query_amounts).fetchdf()
    print(amounts.to_string(index=False))

if __name__ == "__main__":
    analyze_intersections()
