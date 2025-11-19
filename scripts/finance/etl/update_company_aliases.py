from finance_core.db.connector import DBManager

ALIASES = {
    'GGM': ['ГРОСС ГРУП M', 'GROSS_GRUP_M'],
    'GGDI': ['ГРОСС ГРУП ДИ', 'GROSS_GRUP_DI'],
    'YUG_ISTEYT': ['ЮГ ИСТЕЙТ ИНЖИНИРИНГ', 'YuG_ISTEYT_INZhINIRING', 'Юг-Истейт'],
    'GRANDPROM': ['ГРАНДПРОМ'],
    'SGK_REGION': ['СГК-РЕГИОН']
}

def update_aliases():
    db = DBManager().get_arango_db()
    companies = db.collection('Companies')
    
    for key, aliases in ALIASES.items():
        if companies.has(key):
            doc = companies.get(key)
            current_aliases = doc.get('aliases', [])
            # Merge unique
            new_aliases = list(set(current_aliases + aliases))
            doc['aliases'] = new_aliases
            companies.update(doc)
            print(f"✅ Updated aliases for {key}: {new_aliases}")
        else:
            print(f"⚠️ Company {key} not found in DB.")

if __name__ == "__main__":
    update_aliases()
