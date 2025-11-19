from finance_core.db.connector import DBManager

def check_companies():
    db = DBManager().get_arango_db()
    if db.has_collection('Companies'):
        count = db.collection('Companies').count()
        print(f"Companies in ArangoDB: {count}")
        if count > 0:
            for doc in db.collection('Companies').all():
                print(f" - {doc['name']} (Key: {doc['_key']})")
    else:
        print("Companies collection does not exist.")

if __name__ == "__main__":
    check_companies()
