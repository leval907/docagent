import pandas as pd
from pathlib import Path

files = [
    "/opt/1_Project_Alayns/files/Грандпром/ГП 62.01.xls",
    "/opt/1_Project_Alayns/files/Грандпром/osv_detailed_sql_ОСВ_62.01_Grantprom.xlsx"
]

for f in files:
    print(f"\n{'='*50}")
    print(f"DEBUGGING: {Path(f).name}")
    print(f"{'='*50}")
    try:
        df = pd.read_excel(f, header=None, nrows=20)
        print(df.to_string())
    except Exception as e:
        print(f"Error: {e}")
