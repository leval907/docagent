import duckdb
import pandas as pd

DB_PATH = "/opt/docagent/knowledge_base/duckdb/osv/osv_database.duckdb"

conn = duckdb.connect(DB_PATH)

print("📊 Checking Account 91 Items Classification:")

# Check items under 91.01 (Income)
print("\n🟢 91.01 (Прочие доходы) - Top Items:")
res_01 = conn.execute("""
    SELECT item_name, SUM(amount_kt) as total_income
    FROM osv_91 
    WHERE subaccount LIKE '91.01%'
    GROUP BY item_name
    ORDER BY total_income DESC
    LIMIT 20
""").fetchdf()
print(res_01)

# Check items under 91.02 (Expenses)
print("\n🔴 91.02 (Прочие расходы) - Top Items:")
res_02 = conn.execute("""
    SELECT item_name, SUM(amount_dt) as total_expense
    FROM osv_91 
    WHERE subaccount LIKE '91.02%'
    GROUP BY item_name
    ORDER BY total_expense DESC
    LIMIT 20
""").fetchdf()
print(res_02)

conn.close()
