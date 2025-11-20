from arango import ArangoClient
import os

# Config from docker-compose.finance.yml
HOST = "http://localhost:8529"
USER = "root"
PASSWORD = "strongpassword"

try:
    client = ArangoClient(hosts=HOST)
    sys_db = client.db('_system', username=USER, password=PASSWORD)
    
    print("📂 Existing Databases:")
    dbs = sys_db.databases()
    for db in dbs:
        print(f" - {db}")
        
except Exception as e:
    print(f"❌ Error: {e}")
