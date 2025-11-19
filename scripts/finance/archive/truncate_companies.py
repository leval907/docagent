from finance_core.db.connector import DBManager

def truncate_companies():
    db = DBManager().get_arango_db()
    if db.has_collection('Companies'):
        print("🗑 Truncating Companies collection...")
        db.collection('Companies').truncate()
        print("✅ Done.")

if __name__ == "__main__":
    truncate_companies()
