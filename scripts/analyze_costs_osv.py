
import pandas as pd
import sys
import os

# Load the cost mapping
mapping_path = '/opt/docagent/data/cost_mapping.csv'
mapping = pd.read_csv(mapping_path)

# Load the OSV file
file_path = sys.argv[1]
print(f"--- Analyzing Costs for {os.path.basename(file_path)} ---")

try:
    # Read Excel, skipping first few rows to find header
    # We'll try to find the header row that contains 'Счет' or 'Субконто'
    df_raw = pd.read_excel(file_path, header=None)
    
    header_row_idx = None
    for i, row in df_raw.iterrows():
        row_str = str(row.values).lower()
        if 'счет' in row_str and 'сальдо' in row_str:
            header_row_idx = i
            break
    
    if header_row_idx is None:
        # Fallback: try row 6 (index 5) which is common
        header_row_idx = 5
        
    df = pd.read_excel(file_path, header=header_row_idx)
    
    # Identify columns
    # We need 'Счет', 'Субконто' (Cost Item), and 'Оборот Дт' (Debit Turnover)
    # Usually Account is col 0, Subconto is col 1
    
    # Normalize column names
    df.columns = [str(c).strip() for c in df.columns]
    
    account_col = df.columns[0] # Usually 'Счет'
    
    # Find Subconto column (usually contains the cost item name)
    # In 1C OSV, it's often nested or in the first few columns
    # Let's assume it's the column after Account, or we look for specific keywords
    
    # Find Debit Turnover column (Expenses are usually Debit on 20, 26, 44, 91.02)
    debit_col = None
    for c in df.columns:
        c_str = str(c).lower()
        if 'оборот' in c_str and 'дт' in c_str and 'кт' not in c_str: # Pure Debit Turnover
             debit_col = c
             break
        if 'оборот' in c_str and 'дебет' in c_str:
             debit_col = c
             break
        # Sometimes it's just 'Дебет' inside a 'Обороты за период' group, but pandas flattens it differently
        # Let's look for any column containing 'Дт' or 'Дебет' if 'Оборот' is not found directly
    
    if not debit_col:
        # Fallback: look for just 'Оборот Дт' or similar
        possible = [c for c in df.columns if 'оборот' in str(c).lower() and 'дт' in str(c).lower()]
        if possible:
            debit_col = possible[0]
            
    if not debit_col:
        # Fallback 2: Look for column index. Usually:
        # 0: Account
        # 1, 2: Subconto
        # ...
        # Then comes Opening Balance (Dt, Kt)
        # Then Turnover (Dt, Kt)
        # Then Closing Balance (Dt, Kt)
        # If we have ~7-9 columns, Turnover Dt is often around index 4 or 5
        # Let's try to find "Оборот" in the header row values
        pass

    print(f"Account Column: {account_col}")
    print(f"Debit Column: {debit_col}")
    
    if not debit_col:
        print("Could not find Debit Turnover column. Printing columns:")
        print(df.columns.tolist())
        # Try to guess by index if standard structure
        if len(df.columns) >= 7:
             print("Guessing Debit Turnover is column 4 (index 4)")
             debit_col = df.columns[4]
        else:
             sys.exit(1)

    # Filter for Cost Accounts: 20, 26, 44, 91.02
    cost_accounts = ['20', '20.01', '26', '44', '44.01', '44.02', '91.02']
    
    # We need to iterate and extract cost items. 
    # Structure is often hierarchical.
    # Simple approach: Look for rows where Account is in cost_accounts AND Subconto matches a cost item
    
    # Let's try to match by Cost Item Name
    # We'll create a dictionary of Cost Item Name -> (Group, Category)
    cost_map = {}
    for i, row in mapping.iterrows():
        cost_map[str(row['cost_item_name']).lower().strip()] = (row['name_ru_group'], row['name_ru_cat'])
        
    results = []
    
    current_account = None
    
    # Iterate rows
    # In OSV, Account is often only in the header row of a group
    # We need to handle the hierarchy
    
    # Simplified parsing for now:
    # If column 0 is an account, set current_account
    # If column 0 is empty/NaN, check column 1 (Subconto)
    
    # Actually, standard 1C OSV often has Account in col 0 for totals, and Subconto in col 0 indented or col 1
    # Let's look at the dataframe structure
    
    # We will search for strings in the first few columns that match our cost items
    
    total_costs = 0
    mapped_costs = 0
    
    print("\n--- Top Cost Items Found ---")
    print(f"{'Account':<10} | {'Cost Item':<40} | {'Group':<30} | {'Category':<20} | {'Amount':<15}")
    print("-" * 120)
    
    # We'll scan the first string column for matches
    # This is a heuristic
    
    search_cols = df.columns[:3] # Check first 3 columns for text
    
    for i, row in df.iterrows():
        # Determine Account (if present)
        val0 = str(row[df.columns[0]]).strip()
        if val0 in cost_accounts:
            current_account = val0
            continue
        elif val0.split('.')[0] in ['20', '26', '44', '91']: # Starts with cost account
             current_account = val0
        
        # If we are in a cost account context (or if the row itself specifies it)
        # Try to match text
        
        text_val = ""
        for col in search_cols:
            val = str(row[col]).strip()
            if val and val != 'nan' and val != current_account:
                text_val = val
                break
        
        if not text_val:
            continue
            
        # Check if text_val matches a cost item
        text_lower = text_val.lower()
        
        match = None
        # Exact match first
        if text_lower in cost_map:
            match = cost_map[text_lower]
        else:
            # Partial match?
            for key in cost_map:
                if key in text_lower and len(key) > 5: # Avoid short matches
                    match = cost_map[key]
                    break
        
        if match:
            amount = row[debit_col]
            try:
                amount = float(amount)
            except:
                amount = 0
                
            if amount > 0:
                print(f"{str(current_account):<10} | {text_val[:40]:<40} | {match[0][:30]:<30} | {match[1][:20]:<20} | {amount:,.2f}")
                results.append({
                    'Account': current_account,
                    'Cost Item': text_val,
                    'Group': match[0],
                    'Category': match[1],
                    'Amount': amount
                })
                mapped_costs += amount

    print("-" * 120)
    print(f"Total Mapped Costs: {mapped_costs:,.2f}")
    
    # Group by Category and Group
    if results:
        df_res = pd.DataFrame(results)
        print("\n--- Summary by Category ---")
        print(df_res.groupby('Category')['Amount'].sum().apply(lambda x: f"{x:,.2f}"))
        
        print("\n--- Summary by Group ---")
        print(df_res.groupby('Group')['Amount'].sum().sort_values(ascending=False).apply(lambda x: f"{x:,.2f}"))

except Exception as e:
    print(f"Error: {e}")
