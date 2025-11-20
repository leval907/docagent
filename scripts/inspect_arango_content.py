from arango import ArangoClient

HOST = "http://localhost:8529"
USER = "root"
PASSWORD = "strongpassword"

client = ArangoClient(hosts=HOST)

def check_db(name):
    print(f"\n🔍 Checking DB: {name}")
    try:
        if not client.db(name, username=USER, password=PASSWORD).properties():
             print("   ❌ DB does not exist")
             return

        db = client.db(name, username=USER, password=PASSWORD)
        collections = db.collections()
        print(f"   📂 Collections ({len(collections)}):")
        for c in collections:
            if not c['name'].startswith('_'):
                print(f"      - {c['name']} ({c['type']})")
    except Exception as e:
        print(f"   ❌ Error: {e}")

check_db("finance_analytics")
check_db("finance_graph")
