import duckdb
from finance_core.db.connector import DBManager
import re

DB_PATH = '/opt/docagent/temp_osv.duckdb'

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

def sync_companies():
    # 1. Get companies from DuckDB
    con = duckdb.connect(DB_PATH)
    companies = con.execute("SELECT DISTINCT company_name FROM osv_detailed").fetchall()
    company_names = [c[0] for c in companies]
    
    print(f"Found {len(company_names)} companies in DuckDB.")
    
    # 2. Connect to ArangoDB
    db = DBManager().get_arango_db()
    companies_coll = db.collection('Companies')
    companies_coll.truncate() # Clear bad keys
    
    # 3. Sync
    batch = []
    for name in company_names:
        # Transliterate and clean
        transliterated = transliterate(name)
        key = re.sub(r'[^a-zA-Z0-9_]', '', transliterated)
        
        doc = {
            '_key': key,
            'name': name,
            'source': 'DuckDB_Import'
        }
        batch.append(doc)
        print(f"Preparing: {name} -> {key}")
        
    if batch:
        companies_coll.import_bulk(batch, on_duplicate='replace')
        print(f"✅ Synced {len(batch)} companies to ArangoDB.")

if __name__ == "__main__":
    sync_companies()
