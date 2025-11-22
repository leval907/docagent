import duckdb
import pandas as pd
import os

# Config
DB_PATH = "/opt/docagent/knowledge_base/duckdb/osv/osv_database.duckdb"
OUTPUT_FILE = "/opt/docagent/data/osv_revenue_0925/consolidated_balance_sheet.xlsx"

def get_db_connection():
    return duckdb.connect(DB_PATH)

def normalize_name(name):
    if not name:
        return ""
    return str(name).strip().replace('"', '').replace("'", "")

def main():
    print("🚀 Starting Consolidated Balance Sheet Analysis...")
    conn = get_db_connection()
    
    # 1. Get Group Companies
    print("📦 Loading Group Companies...")
    group_companies_df = conn.execute("SELECT DISTINCT company_name FROM group_companies").fetchdf()
    group_companies = set([normalize_name(x) for x in group_companies_df['company_name'].tolist()])
    print(f"   Found {len(group_companies)} group companies.")

    # 2. Load General OSV (All Accounts)
    print("📊 Loading General OSV Data (Start & End Balances)...")
    
    # Fetch Start and End balances
    query_general = """
    SELECT 
        company_raw, 
        account, 
        SUM(start_dt) as start_asset,
        SUM(start_kt) as start_liab,
        SUM(end_dt) as end_asset, 
        SUM(end_kt) as end_liab
    FROM osv_general
    GROUP BY company_raw, account
    """
    general_df = conn.execute(query_general).fetchdf()
    general_df['company_norm'] = general_df['company_raw'].apply(normalize_name)
    
    # 3. Categorize Accounts
    def categorize_account(row):
        acc = str(row['account']).split('.')[0] # Get top level account
        
        # Assets
        if acc in ['50', '51', '52', '55', '57']: return 'Cash'
        if acc in ['62']: return 'AccountsReceivable'
        if acc in ['10', '20', '21', '23', '25', '26', '29', '41', '43', '44', '45', '97']: return 'Inventory_WIP'
        if acc in ['01', '03', '04', '08']: return 'FixedAssets'
        if acc in ['02', '05']: return 'Depreciation'
        if acc in ['19']: return 'VAT_Receivable'
        
        # Liabilities
        if acc in ['60']: return 'AccountsPayable'
        if acc in ['66', '67']: return 'Loans'
        if acc in ['68', '69', '70']: return 'Taxes_Wages'
        
        # Mixed / Other
        if acc in ['71', '73', '75', '76', '79']: return 'Other_AR_AP'
        
        # Equity
        if acc in ['80', '82', '83']: return 'Equity_Capital'
        if acc in ['84', '99', '90', '91']: return 'RetainedEarnings'
        
        return 'Unclassified'

    general_df['category'] = general_df.apply(categorize_account, axis=1)
    
    # 4. Build Aggregated Balance Sheet (Before Eliminations)
    print("∑  Aggregating Balances...")
    
    # Pivot or Group by Category
    balance_summary = general_df.groupby('category')[['start_asset', 'start_liab', 'end_asset', 'end_liab']].sum().reset_index()
    
    # 5. Identify Intercompany (Eliminations)
    print("🕵️  Identifying Intercompany Transactions (Start & End)...")
    
    # We calculate eliminations for both Start and End periods
    query_60 = """
    SELECT 
        company_raw, 
        counterparty, 
        SUM(initial_balance_kt) as start_debt,
        SUM(final_balance_kt) as end_debt
    FROM osv_60
    WHERE final_balance_kt > 0 OR initial_balance_kt > 0
    GROUP BY company_raw, counterparty
    """
    ap_details = conn.execute(query_60).fetchdf()
    ap_details['company_norm'] = ap_details['company_raw'].apply(normalize_name)
    ap_details['counterparty_norm'] = ap_details['counterparty'].apply(normalize_name)
    
    # Filter Intercompany
    intercompany_ap = ap_details[
        ap_details['counterparty_norm'].isin(group_companies)
    ].copy()
    
    elim_start = intercompany_ap['start_debt'].sum()
    elim_end = intercompany_ap['end_debt'].sum()
    
    print(f"   Intercompany AP Start: {elim_start:,.2f}")
    print(f"   Intercompany AP End:   {elim_end:,.2f}")
    
    # 6. Create Final Report
    print("📝 Generating Excel Report...")
    
    with pd.ExcelWriter(OUTPUT_FILE, engine='xlsxwriter') as writer:
        # Sheet 1: Raw Data by Company
        general_df.to_excel(writer, sheet_name='Raw_Balances', index=False)
        
        # Sheet 2: Aggregated Balance (Before)
        balance_summary.to_excel(writer, sheet_name='Aggregated_Before', index=False)
        
        # Sheet 3: Intercompany Matrix (End Period)
        if not intercompany_ap.empty:
            matrix = intercompany_ap.pivot_table(
                index='company_norm', 
                columns='counterparty_norm', 
                values='end_debt', 
                aggfunc='sum'
            ).fillna(0)
            matrix.to_excel(writer, sheet_name='Intercompany_Matrix_End')
        
        # Sheet 4: Consolidated Balance (After)
        cons_balance = balance_summary.copy()
        cons_balance.set_index('category', inplace=True)
        
        # Apply Eliminations (Start & End)
        if 'AccountsPayable' in cons_balance.index:
            cons_balance.loc['AccountsPayable', 'start_liab'] -= elim_start
            cons_balance.loc['AccountsPayable', 'end_liab']   -= elim_end
            
        if 'AccountsReceivable' in cons_balance.index:
            cons_balance.loc['AccountsReceivable', 'start_asset'] -= elim_start
            cons_balance.loc['AccountsReceivable', 'end_asset']   -= elim_end
            
        cons_balance.reset_index().to_excel(writer, sheet_name='Consolidated_After', index=False)
        
    print(f"🎉 Report saved to: {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
