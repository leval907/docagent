
import pandas as pd
import sys

file_path = sys.argv[1]
print(f"--- Inspecting {file_path} ---")

df = pd.read_excel(file_path, header=None)
print(df.head(15))
