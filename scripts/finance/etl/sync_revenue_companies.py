import pandas as pd
from finance_core.db.connector import DBManager
import re

FILE_PATH = '/opt/docagent/data/osv_revenue_0925/output/consolidated_revenue.xlsx'
GROUP_NAME = 'Main_Group'

def transliterate(text):
    mapping = {
        'а': 'a', 'б': 'b', 'в': 'v', 'г': 'g', 'д': 'd', 'е': 'e', 'ё': 'yo',
        'ж': 'zh', 'з': 'z', 'и': 'i', 'й': 'y', 'к': 'k', 'л': 'l', 'м': 'm',
        'н': 'n', 'о': 'o', 'п': 'p', 'р': 'r', 'с': 's', 'т': 't', 'у': 'u',
        'ф': 'f', 'х': 'kh', 'ц': 'ts', 'ч': 'ch', 'ш': 'sh', 'щ': 'shch',
        'ъ': '', 'ы': 'y', 'ь': '', 'э': 'e', 'ю': 'yu', 'я': 'ya',
        'А': 'A', 'Б': 'B', 'В': 'V', 'Г': 'G', 'Д': 'D', 'Е': 'E', 'Ё': 'Yo',
        'Ж': 'Zh', 'З': 'Z', 'И': 'I', 'Й': 'Y', 'К': 'K', 'Л': 'L', 'М': 'M',
        'Н': 'N', 'О': 'O', 'П': 'P', 'Р': 'R', 'С': 'S', 'Т': 'T', 'У': 'U',
        'Ф': 'F', 'Х': 'Kh', 'Ц': 'Ts', 'Ч': 'Ch', 'Ш': 'Sh', 'Щ': 'Shch',
        'Ъ': '', 'Ы': 'Y', 'Ь': '', 'Э': 'E', 'Ю': 'Yu', 'Я': 'Ya',
        ' ': '_', '-': '_'
    }
    result = ''
    for char in text:
        result += mapping.get(char, char)
    return result

def sync_group_companies():
    print(f"📂 Reading companies from: {FILE_PATH}")
    df = pd.read_excel(FILE_PATH)
    
    db = DBManager().get_arango_db()
    companies_coll = db.collection('Companies')
    
    batch = []
    for _, row in df.iterrows():
        name = str(row['Компания']).strip()
        if not name or name.lower() == 'nan':
            continue
            
        # Transliterate and clean
        transliterated = transliterate(name)
        key = re.sub(r'[^a-zA-Z0-9_]', '', transliterated).upper()
        
        if 'ITOGO' in key:
            continue
        
        doc = {
            '_key': key,
            'name': name,
            'group': GROUP_NAME,
            'source': 'Consolidated_Revenue_XLSX',
            # We can also store revenue summary here if we want, but better in FinancialData
            'revenue_total': float(row['выручка_всего']) if pd.notna(row['выручка_всего']) else 0.0
        }
        batch.append(doc)
        print(f"Preparing: {name} -> {key} (Group: {GROUP_NAME})")
        
    if batch:
        companies_coll.import_bulk(batch, on_duplicate='update')
        print(f"✅ Synced {len(batch)} companies to ArangoDB.")

if __name__ == "__main__":
    sync_group_companies()
