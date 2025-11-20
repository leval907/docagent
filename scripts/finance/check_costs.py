import duckdb
import pandas as pd

DB_PATH = "/opt/docagent/knowledge_base/duckdb/osv/osv_database.duckdb"

conn = duckdb.connect(DB_PATH)

print("📊 Summary of 'osv_costs' table:")
summary = conn.execute("""
    SELECT 
        account_type, 
        COUNT(*) as record_count, 
        SUM(amount_dt) as total_debit, 
        SUM(amount_kt) as total_credit,
        COUNT(DISTINCT company_raw) as companies
    FROM osv_costs
    GROUP BY account_type
    ORDER BY account_type
""").fetchdf()
print(summary)

print("\n📊 Top 5 Cost Items for Account 20:")
top20 = conn.execute("""
    SELECT cost_item, SUM(amount_dt) as total 
    FROM osv_costs 
    WHERE account_type = '20' 
    GROUP BY cost_item 
    ORDER BY total DESC 
    LIMIT 5
""").fetchdf()
print(top20)

print("\n📊 Top 5 Cost Items for Account 26:")
top26 = conn.execute("""
    SELECT cost_item, SUM(amount_dt) as total 
    FROM osv_costs 
    WHERE account_type = '26' 
    GROUP BY cost_item 
    ORDER BY total DESC 
    LIMIT 5
""").fetchdf()
print(top26)

conn.close()
