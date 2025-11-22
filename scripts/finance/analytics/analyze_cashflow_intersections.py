import duckdb
import pandas as pd

DB_PATH = "/opt/docagent/knowledge_base/duckdb/osv/osv_database.duckdb"

def analyze_cashflow():
    conn = duckdb.connect(DB_PATH)
    
    print("🔍 Analyzing Intercompany Cash Flows (Proxy via 60/62 Turnovers)...")
    
    # 1. Identify Group Companies
    # We assume companies appearing in 'company_raw' are the group members.
    # We also need to normalize names to match 'counterparty' fields (often slightly different).
    
    companies_df = conn.execute("SELECT DISTINCT company_raw FROM osv_general").fetchdf()
    group_companies = [c for c in companies_df['company_raw'].dropna().unique() if c.strip()]
    
    print(f"🏢 Identified Group Companies ({len(group_companies)}):")
    for c in group_companies:
        print(f"   - {c}")
        
    # We need a fuzzy match or a normalized list because 'company_raw' might be "ГРАНДПРОМ" 
    # but counterparty might be "ГРАНДПРОМ АО" or "АО ГРАНДПРОМ".
    # For this script, we will try to match by checking if the company name is part of the counterparty string.
    
    # Let's create a SQL list for exact matches first, but we'll do filtering in Python for better fuzzy matching.
    
    # 2. Fetch Data
    df_60 = conn.execute("SELECT company_raw, counterparty, turnover_dt, turnover_kt FROM osv_60").fetchdf()
    df_62 = conn.execute("SELECT company_raw, counterparty, turnover_dt, turnover_kt FROM osv_62").fetchdf()
    
    # 3. Analyze Payments MADE (Debit Turnover of 60)
    # Logic: Company A (company_raw) pays Supplier B (counterparty). 
    # If Supplier B is in Group, it's an intercompany payment.
    
    print("\n💸 Intercompany Payments (Cash Outflow) - Based on Account 60 Debit Turnover:")
    print(f"{'Payer (Company)':<30} | {'Receiver (Counterparty)':<40} | {'Amount (Rub)':<20}")
    print("-" * 95)
    
    total_payments = 0
    
    # Helper to check if counterparty is in group
    def is_group_member(name, group_list):
        if not isinstance(name, str): return False
        
        def clean_name(n):
            n = n.lower()
            # Remove quotes
            n = n.replace('"', '').replace("'", "").replace("«", "").replace("»", "")
            # Remove legal forms (Cyrillic and Latin)
            n = n.replace('ооо', '').replace('ooo', '') # Cyrillic ooo, Latin ooo
            n = n.replace('ао', '').replace('ao', '')   # Cyrillic ao, Latin ao
            n = n.replace('зао', '').replace('zao', '')
            n = n.replace('ип', '').replace('ip', '')
            return n.strip()

        name_clean = clean_name(name)
        
        for g in group_list:
            g_clean = clean_name(g)
            
            # Exact match after cleaning
            if g_clean == name_clean:
                return True
                
            # Substring match (be careful with short names)
            if len(g_clean) > 3 and len(name_clean) > 3:
                if g_clean in name_clean or name_clean in g_clean:
                    return True
                    
        return False

    ic_payments = []
    for _, row in df_60.iterrows():
        if is_group_member(row['counterparty'], group_companies):
            # Exclude self-references if any
            if row['company_raw'].lower() not in row['counterparty'].lower():
                if row['turnover_dt'] > 0:
                    ic_payments.append({
                        'payer': row['company_raw'],
                        'receiver': row['counterparty'],
                        'amount': row['turnover_dt']
                    })

    ic_payments_df = pd.DataFrame(ic_payments)
    if not ic_payments_df.empty:
        ic_payments_df = ic_payments_df.sort_values(by='amount', ascending=False)
        for _, row in ic_payments_df.iterrows():
            print(f"{row['payer']:<30} | {row['receiver']:<40} | {row['amount']:,.2f}")
            total_payments += row['amount']
    else:
        print("   No intercompany payments found in Account 60.")
        
    print(f"{'-'*95}")
    print(f"{'TOTAL':<73} | {total_payments:,.2f}")


    # 4. Analyze Payments RECEIVED (Credit Turnover of 62)
    # Logic: Company A (company_raw) receives from Buyer B (counterparty).
    # If Buyer B is in Group, it's an intercompany receipt.
    
    print("\n💰 Intercompany Receipts (Cash Inflow) - Based on Account 62 Credit Turnover:")
    print(f"{'Receiver (Company)':<30} | {'Payer (Counterparty)':<40} | {'Amount (Rub)':<20}")
    print("-" * 95)
    
    total_receipts = 0
    ic_receipts = []
    
    for _, row in df_62.iterrows():
        if is_group_member(row['counterparty'], group_companies):
             # Exclude self-references
            if row['company_raw'].lower() not in row['counterparty'].lower():
                if row['turnover_kt'] > 0:
                    ic_receipts.append({
                        'receiver': row['company_raw'],
                        'payer': row['counterparty'],
                        'amount': row['turnover_kt']
                    })
                    
    ic_receipts_df = pd.DataFrame(ic_receipts)
    if not ic_receipts_df.empty:
        ic_receipts_df = ic_receipts_df.sort_values(by='amount', ascending=False)
        for _, row in ic_receipts_df.iterrows():
            print(f"{row['receiver']:<30} | {row['payer']:<40} | {row['amount']:,.2f}")
            total_receipts += row['amount']
    else:
        print("   No intercompany receipts found in Account 62.")

    print(f"{'-'*95}")
    print(f"{'TOTAL':<73} | {total_receipts:,.2f}")
    
    print("\n⚖️  CROSS-CHECK:")
    print(f"Total Payments Detected (60 Dt): {total_payments:,.2f}")
    print(f"Total Receipts Detected (62 Kt): {total_receipts:,.2f}")
    diff = total_payments - total_receipts
    print(f"Difference: {diff:,.2f}")
    if abs(diff) > 1000:
        print("⚠️  Mismatch suggests:")
        print("    1. Timing differences (money in transit).")
        print("    2. Classification differences (one booked as 60, other as 76 or 66/67).")
        print("    3. Missing data (some companies' OSV might be missing).")
    else:
        print("✅ Perfect Match!")

if __name__ == "__main__":
    analyze_cashflow()
