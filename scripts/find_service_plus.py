import pandas as pd
import sys

def find_service_plus(file_path):
    try:
        df = pd.read_excel(file_path, header=1) # Assuming header is at row 1 (index 1) based on previous run
        # Filter for Service Plus
        row = df[df['Контрагент'].astype(str).str.contains("СЕРВИС ПЛЮС", na=False)]
        if not row.empty:
            print(row.iloc[0])
        else:
            print("Not found")
    except Exception as e:
        print(e)

if __name__ == "__main__":
    find_service_plus(sys.argv[1])
