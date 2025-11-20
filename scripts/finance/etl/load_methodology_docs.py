#!/usr/bin/env python3
"""
ETL Script: Load Methodology Documents into ArangoDB.
Parses the markdown file, stores it in 'Documents' collection,
and creates 'Mentions' edges to referenced Accounts.
"""

from arango import ArangoClient
import hashlib
import re
from pathlib import Path
import datetime

# === Config ===
ARANGO_HOST = "http://localhost:8529"
ARANGO_USER = "root"
ARANGO_PASS = "strongpassword"
DB_NAME = "finance_analytics"

DOC_PATH = Path("/opt/docagent/data/osv_revenue_0925/input/info_docs/METHODOLOGY_BALANCE_LIQUIDITY.md")

# === Helpers ===
def make_key(text):
    return hashlib.md5(text.strip().lower().encode('utf-8')).hexdigest()

def main():
    print(f"🚀 Loading Methodology: {DOC_PATH.name}")
    
    if not DOC_PATH.exists():
        print(f"❌ File not found: {DOC_PATH}")
        return

    # 1. Connect to DB
    client = ArangoClient(hosts=ARANGO_HOST)
    db = client.db(DB_NAME, username=ARANGO_USER, password=ARANGO_PASS)
    
    docs_col = db.collection('Documents')
    mentions_col = db.collection('Mentions')
    accounts_col = db.collection('Accounts')

    # 2. Read Content
    content = DOC_PATH.read_text(encoding='utf-8')
    
    # 3. Create Document Node
    doc_key = make_key(DOC_PATH.name)
    doc_data = {
        '_key': doc_key,
        'title': "Методика формирования Баланса и Отчетности по ОСВ",
        'type': 'methodology',
        'content': content,
        'source_path': str(DOC_PATH),
        'created_at': datetime.datetime.now().isoformat(),
        'tags': ['balance', 'liquidity', 'methodology', 'osv']
    }
    
    if docs_col.has(doc_key):
        docs_col.update(doc_data)
        print(f"   🔄 Updated Document: {doc_data['title']}")
    else:
        docs_col.insert(doc_data)
        print(f"   ✅ Created Document: {doc_data['title']}")

    # 4. Extract Mentions (Accounts)
    # Regex to find patterns like "Счет 51", "Дт 51", "Кт 60", or just "51" in table context if possible.
    # Simple approach: find all 2-digit numbers that match known accounts.
    
    # Get all known accounts from DB to filter false positives
    known_accounts = set()
    for acc in accounts_col.all():
        known_accounts.add(acc['_key'])
        
    print(f"   ℹ️  Known accounts in DB: {known_accounts}")

    # Find mentions in text
    # Pattern: Look for "счет XX", "Дт XX", "Кт XX" or just "XX" inside tables/lists
    # Let's try a broader search for 2-digit numbers and check against known_accounts
    found_accounts = set()
    
    # Regex for "Account XX" or "Dt/Kt XX" or just "XX" surrounded by spaces/punctuation
    matches = re.findall(r'\b(\d{2})\b', content)
    
    for acc_code in matches:
        if acc_code in known_accounts:
            found_accounts.add(acc_code)
            
    # Also check for subaccounts like 90.01, 91.02 (take first 2 digits)
    matches_sub = re.findall(r'\b(\d{2})\.\d{2}\b', content)
    for acc_code in matches_sub:
        if acc_code in known_accounts:
            found_accounts.add(acc_code)

    print(f"   🔍 Found account mentions: {found_accounts}")

    # 5. Create Edges
    # Remove old mentions from this doc first (to avoid duplicates on re-run)
    # AQL: FOR e IN Mentions FILTER e._from == @doc_id REMOVE e IN Mentions
    db.aql.execute("""
        FOR e IN Mentions 
        FILTER e._from == @doc_id 
        REMOVE e IN Mentions
    """, bind_vars={'doc_id': f"Documents/{doc_key}"})
    
    count = 0
    for acc_code in found_accounts:
        edge = {
            '_from': f"Documents/{doc_key}",
            '_to': f"Accounts/{acc_code}",
            'type': 'mentions_account',
            'context': 'methodology_reference'
        }
        mentions_col.insert(edge)
        count += 1
        
    print(f"   🔗 Created {count} Mention edges to Accounts")
    print("🎉 Done!")

if __name__ == "__main__":
    main()
