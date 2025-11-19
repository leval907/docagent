import pandas as pd

FILE_PATH = '/opt/docagent/data/osv_revenue_0925/input/исп_9.2025 ВФЦ.xlsx'

def inspect_osv_file():
    try:
        # Read without header first to see structure
        df = pd.read_excel(FILE_PATH, header=None, nrows=20)
        print(f"📂 File: {FILE_PATH}")
        print("\n   Sample Data (First 20 rows):")
        print(df.to_string())
    except Exception as e:
        print(f"❌ Error reading file: {e}")

if __name__ == "__main__":
    inspect_osv_file()
