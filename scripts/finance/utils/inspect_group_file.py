import pandas as pd

FILE_PATH = '/opt/docagent/data/osv_revenue_0925/input/Группа Компаний_А.xlsx'

def inspect_group_file():
    try:
        df = pd.read_excel(FILE_PATH)
        print(f"📂 File: {FILE_PATH}")
        print(f"   Rows: {len(df)}")
        print(f"   Columns: {list(df.columns)}")
        print("\n   Sample Data:")
        print(df.head().to_string())
        
        # Try to find company names column
        possible_cols = [c for c in df.columns if 'компани' in str(c).lower() or 'название' in str(c).lower() or 'name' in str(c).lower()]
        if possible_cols:
            print(f"\n   Potential Company Columns: {possible_cols}")
            for col in possible_cols:
                print(f"   Values in {col}:")
                print(df[col].unique())
                
    except Exception as e:
        print(f"❌ Error reading file: {e}")

if __name__ == "__main__":
    inspect_group_file()
