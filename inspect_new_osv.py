import pandas as pd
import sys

FILE_PATH = "/opt/docagent/data/osv_revenue_0925/input/osv_60_9m/60/01-60 Альянс.xlsx"

print(f"Inspecting: {FILE_PATH}")

try:
    # Try reading with default header
    df = pd.read_excel(FILE_PATH, header=None, nrows=20)
    print("\nFirst 10 rows (header=None):")
    print(df.to_string())
except Exception as e:
    print(f"Error reading file: {e}")
