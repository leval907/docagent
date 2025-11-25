import pandas as pd
import sys
import os

def analyze_revenue(file_path):
    print(f"--- Analyzing {os.path.basename(file_path)} ---")
    try:
        # Load the excel file
        # Try to find the header row
        df_raw = pd.read_excel(file_path, header=None)
        header_row_idx = None
        for i, row in df_raw.iterrows():
            row_values = [str(v).lower() for v in row.values]
            if 'контрагент' in row_values or 'контрагенты' in row_values:
                header_row_idx = i
                break
        
        if header_row_idx is not None:
            print(f"Found header at row {header_row_idx}")
            df = pd.read_excel(file_path, header=header_row_idx)
        else:
            print("Could not find header row with 'Контрагент'. Using default.")
            df = pd.read_excel(file_path)
            
        print("Columns:", df.columns.tolist())
        
        # Try to identify relevant columns
        # Usually 'Контрагент' (Counterparty) and 'Сумма' (Amount) or similar
        
        # Let's look for columns that might contain counterparty names
        counterparty_col = None
        amount_col = None
        
        for col in df.columns:
            if 'контрагент' in str(col).lower() or 'покупатель' in str(col).lower():
                counterparty_col = col
            # if 'сумма' in str(col).lower() or 'оборот' in str(col).lower():
            #    amount_col = col
        
        if counterparty_col:
             # Fallback: try to find the best amount column if the default logic failed or picked a wrong one
             # Look for columns with '51' (Bank) and '62' (Sales) in the name, usually Credit 62 or Debit 51
             # Also look for '90' (Sales) and '62' (Receivables) for accrued revenue
             possible_amount_cols = [c for c in df.columns if ('51' in str(c) and '62' in str(c)) or ('90' in str(c) and '62' in str(c))]
             if possible_amount_cols:
                 print(f"Detected possible amount columns: {possible_amount_cols}")
                 for col in possible_amount_cols:
                     print(f"--- Analysis for {col} ---")
                     # Group by counterparty and sum amount
                     summary = df.groupby(counterparty_col)[col].sum().sort_values(ascending=False).head(10)
                     
                     # For each top counterparty, find the most frequent payment purpose (Basis)
                     print(f"{'Counterparty':<50} | {'Amount':<15} | {'Top Purpose (Basis)'}")
                     print("-" * 100)
                     
                     basis_col = None
                     for c in df.columns:
                         if 'основание' in str(c).lower() or 'назначение' in str(c).lower():
                             basis_col = c
                             break
                     
                     for partner, amount in summary.items():
                         purpose = "N/A"
                         if basis_col:
                             # Get the most frequent purpose for this partner
                             purposes = df[df[counterparty_col] == partner][basis_col].value_counts()
                             if not purposes.empty:
                                 purpose = purposes.index[0]
                                 # Truncate long purposes
                                 if len(str(purpose)) > 50:
                                     purpose = str(purpose)[:47] + "..."
                         
                         print(f"{str(partner):<50} | {amount:,.2f}       | {purpose}")
                         
                     print(f"\nTotal Top 10: {summary.sum():,.2f}")
                     print(f"Total Column: {df[col].sum():,.2f}\n")
             else:
                 print("No obvious amount column found.")
        else:
            print("Could not automatically identify Counterparty/Amount columns.")
            print("First 5 rows:")
            print(df.head())

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python analyze_revenue.py <file_path>")
        sys.exit(1)
    
    analyze_revenue(sys.argv[1])
