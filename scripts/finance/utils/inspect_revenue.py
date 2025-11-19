import pandas as pd

FILE_PATH = '/opt/docagent/data/osv_revenue_0925/output/consolidated_revenue.xlsx'

def inspect_excel():
    try:
        df = pd.read_excel(FILE_PATH)
        print(f"📂 File: {FILE_PATH}")
        print(f"   Rows: {len(df)}")
        print(f"   Columns: {list(df.columns)}")
        print("\n   Sample Data:")
        print(df.head().to_string())
    except Exception as e:
        print(f"❌ Error reading file: {e}")

if __name__ == "__main__":
    inspect_excel()
