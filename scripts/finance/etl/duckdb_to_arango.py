#!/usr/bin/env python3
"""
ETL Script: Transfer data from DuckDB to ArangoDB.
Populates Companies, Accounts, CostItems, and creates edges for Costs, CashFlow, and Supplier Transactions.
"""

import duckdb
from arango import ArangoClient
import hashlib
import re

# === Config ===
DUCKDB_PATH = "/opt/docagent/knowledge_base/duckdb/osv/osv_database.duckdb"
ARANGO_HOST = "http://localhost:8529"
ARANGO_USER = "root"
ARANGO_PASS = "strongpassword"
DB_NAME = "finance_analytics"

# === Helpers ===
def make_key(text):
    """Creates a safe key for ArangoDB from a string."""
    if not text:
        return "unknown"
    # Transliterate or hash? Hash is safer for arbitrary text.
    return hashlib.md5(text.strip().lower().encode('utf-8')).hexdigest()

def normalize_company_name(name):
    """Simple normalization for company names."""
    if not name:
        return "Unknown"
    name = str(name).strip().replace('"', '').replace("'", "")
    return name

# === Main ETL Class ===
class DuckToArangoETL:
    def __init__(self):
        self.duck_conn = duckdb.connect(DUCKDB_PATH)
        self.client = ArangoClient(hosts=ARANGO_HOST)
        self.db = self.client.db(DB_NAME, username=ARANGO_USER, password=ARANGO_PASS)
        
    def run(self):
        print("🚀 Starting ETL: DuckDB -> ArangoDB")
        
        self.sync_companies()
        self.sync_accounts()
        self.sync_cost_items()
        self.sync_costs_incurred() # 20, 26, 44, 91, 51
        self.sync_supplier_transactions() # 60
        
        print("🎉 ETL Complete!")

    def sync_companies(self):
        print("\n📦 Syncing Companies...")
        # 1. Group Companies
        companies = self.duck_conn.execute("SELECT DISTINCT company_name FROM group_companies").fetchdf()
        col = self.db.collection('Companies')
        
        count = 0
        for _, row in companies.iterrows():
            name = normalize_company_name(row['company_name'])
            key = make_key(name)
            doc = {
                '_key': key,
                'name': name,
                'is_group': True
            }
            if not col.has(key):
                col.insert(doc)
                count += 1
        print(f"   ✅ Added {count} group companies")

    def sync_accounts(self):
        print("\n📦 Syncing Accounts...")
        accounts = [
            {'code': '20', 'name': 'Основное производство', 'type': 'Active'},
            {'code': '26', 'name': 'Общехозяйственные расходы', 'type': 'Active'},
            {'code': '44', 'name': 'Расходы на продажу', 'type': 'Active'},
            {'code': '51', 'name': 'Расчетные счета', 'type': 'Active'},
            {'code': '60', 'name': 'Расчеты с поставщиками', 'type': 'Passive'},
            {'code': '91', 'name': 'Прочие доходы и расходы', 'type': 'ActivePassive'},
        ]
        col = self.db.collection('Accounts')
        for acc in accounts:
            if not col.has(acc['code']):
                col.insert({'_key': acc['code'], **acc})
        print(f"   ✅ Synced {len(accounts)} accounts")

    def sync_cost_items(self):
        print("\n📦 Syncing Cost Items (Dictionary)...")
        col = self.db.collection('CostItems')
        
        # 1. From osv_costs (20, 26, 44)
        items_costs = self.duck_conn.execute("SELECT DISTINCT cost_item FROM osv_costs").fetchdf()
        count = 0
        for _, row in items_costs.iterrows():
            name = str(row['cost_item']).strip()
            key = make_key(name)
            if not col.has(key):
                col.insert({'_key': key, 'name': name, 'type': 'production_cost'})
                count += 1
                
        # 2. From osv_91
        items_91 = self.duck_conn.execute("SELECT DISTINCT item_name FROM osv_91").fetchdf()
        for _, row in items_91.iterrows():
            name = str(row['item_name']).strip()
            key = make_key(name)
            if not col.has(key):
                col.insert({'_key': key, 'name': name, 'type': 'other_income_expense'})
                count += 1
                
        # 3. From osv_51 (DDS Items)
        items_51 = self.duck_conn.execute("SELECT DISTINCT dds_item FROM osv_51").fetchdf()
        for _, row in items_51.iterrows():
            name = str(row['dds_item']).strip()
            key = make_key(name)
            if not col.has(key):
                col.insert({'_key': key, 'name': name, 'type': 'cash_flow_item'})
                count += 1
                
        print(f"   ✅ Added {count} new cost/cashflow items")

    def sync_costs_incurred(self):
        print("\n🔗 Creating 'Incurred' Edges (Costs & CashFlow)...")
        edge_col = self.db.collection('Incurred')
        edge_col.truncate() # Full refresh for simplicity
        
        # 1. Production Costs (20, 26, 44)
        costs = self.duck_conn.execute("""
            SELECT company_raw, account_type, cost_item, SUM(amount_dt) as amount 
            FROM osv_costs 
            GROUP BY company_raw, account_type, cost_item
        """).fetchdf()
        
        count = 0
        for _, row in costs.iterrows():
            comp_key = make_key(normalize_company_name(row['company_raw']))
            item_key = make_key(str(row['cost_item']).strip())
            
            # Ensure nodes exist (Company might be missing if not in group list, but we try)
            # In a real scenario, we'd handle missing companies gracefully or add them.
            
            doc = {
                '_from': f"Companies/{comp_key}",
                '_to': f"CostItems/{item_key}",
                'account': row['account_type'],
                'amount': row['amount'],
                'period': '9_months_2025',
                'type': 'production'
            }
            edge_col.insert(doc)
            count += 1
            
        # 2. Other Income/Expense (91)
        # 91.02 is Expense (Dt), 91.01 is Income (Kt)
        # We will store both as 'Incurred' but with direction/type? 
        # Or maybe 'Incurred' implies expense. For Income, maybe we need 'Generated'?
        # For now, let's put everything in Incurred with a 'sign' or 'category'.
        
        # Expenses (91.02)
        exps_91 = self.duck_conn.execute("""
            SELECT company_raw, item_name, SUM(amount_dt) as amount 
            FROM osv_91 WHERE subaccount LIKE '91.02%'
            GROUP BY company_raw, item_name
        """).fetchdf()
        
        for _, row in exps_91.iterrows():
            comp_key = make_key(normalize_company_name(row['company_raw']))
            item_key = make_key(str(row['item_name']).strip())
            
            doc = {
                '_from': f"Companies/{comp_key}",
                '_to': f"CostItems/{item_key}",
                'account': '91.02',
                'amount': row['amount'],
                'period': '9_months_2025',
                'type': 'other_expense'
            }
            edge_col.insert(doc)
            count += 1

        # Income (91.01) - Technically not "Incurred", but let's store it for now
        # Maybe we should have a separate edge for Income? Or just use type='income'
        inc_91 = self.duck_conn.execute("""
            SELECT company_raw, item_name, SUM(amount_kt) as amount 
            FROM osv_91 WHERE subaccount LIKE '91.01%'
            GROUP BY company_raw, item_name
        """).fetchdf()
        
        for _, row in inc_91.iterrows():
            comp_key = make_key(normalize_company_name(row['company_raw']))
            item_key = make_key(str(row['item_name']).strip())
            
            doc = {
                '_from': f"Companies/{comp_key}",
                '_to': f"CostItems/{item_key}",
                'account': '91.01',
                'amount': row['amount'],
                'period': '9_months_2025',
                'type': 'other_income'
            }
            edge_col.insert(doc)
            count += 1
            
        # 3. Cash Flow (51)
        # Inflow and Outflow
        cash = self.duck_conn.execute("""
            SELECT company_raw, dds_item, SUM(inflow) as inflow, SUM(outflow) as outflow
            FROM osv_51
            GROUP BY company_raw, dds_item
        """).fetchdf()
        
        for _, row in cash.iterrows():
            comp_key = make_key(normalize_company_name(row['company_raw']))
            item_key = make_key(str(row['dds_item']).strip())
            
            if row['outflow'] > 0:
                edge_col.insert({
                    '_from': f"Companies/{comp_key}",
                    '_to': f"CostItems/{item_key}",
                    'account': '51',
                    'amount': row['outflow'],
                    'period': '9_months_2025',
                    'type': 'cash_outflow'
                })
                count += 1
            
            if row['inflow'] > 0:
                edge_col.insert({
                    '_from': f"Companies/{comp_key}",
                    '_to': f"CostItems/{item_key}",
                    'account': '51',
                    'amount': row['inflow'],
                    'period': '9_months_2025',
                    'type': 'cash_inflow'
                })
                count += 1

        print(f"   ✅ Created {count} Incurred/Flow edges")

    def sync_supplier_transactions(self):
        print("\n🔗 Creating 'Transactions' Edges (Suppliers 60)...")
        # We need to ensure Counterparties exist in Companies
        
        # 1. Get all counterparties
        suppliers = self.duck_conn.execute("""
            SELECT DISTINCT counterparty FROM osv_60
        """).fetchdf()
        
        comp_col = self.db.collection('Companies')
        new_comps = 0
        for _, row in suppliers.iterrows():
            name = normalize_company_name(row['counterparty'])
            key = make_key(name)
            if not comp_col.has(key):
                comp_col.insert({
                    '_key': key,
                    'name': name,
                    'is_group': False, # External by default
                    'type': 'counterparty'
                })
                new_comps += 1
        print(f"   ✅ Added {new_comps} external counterparties")
        
        # 2. Create Transactions
        trans_col = self.db.collection('Transactions')
        trans_col.truncate()
        
        data = self.duck_conn.execute("""
            SELECT company_raw, counterparty, 
                   SUM(turnover_dt) as turn_dt, 
                   SUM(turnover_kt) as turn_kt,
                   SUM(final_balance_kt) as debt
            FROM osv_60
            GROUP BY company_raw, counterparty
        """).fetchdf()
        
        count = 0
        for _, row in data.iterrows():
            our_key = make_key(normalize_company_name(row['company_raw']))
            supp_key = make_key(normalize_company_name(row['counterparty']))
            
            # If Turnover Kt > 0 (We owe them / They provided service)
            # Let's represent this as a transaction flow?
            # Or just a summary edge.
            
            if row['turn_kt'] > 0 or row['turn_dt'] > 0 or row['debt'] > 0:
                doc = {
                    '_from': f"Companies/{our_key}",
                    '_to': f"Companies/{supp_key}",
                    'account': '60',
                    'turnover_dt': row['turn_dt'], # We paid / Advance
                    'turnover_kt': row['turn_kt'], # They invoiced
                    'debt_end': row['debt'],
                    'period': '9_months_2025',
                    'type': 'supplier_relation'
                }
                trans_col.insert(doc)
                count += 1
                
        print(f"   ✅ Created {count} Supplier transaction edges")

if __name__ == "__main__":
    etl = DuckToArangoETL()
    etl.run()
