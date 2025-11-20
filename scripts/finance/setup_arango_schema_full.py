#!/usr/bin/env python3
"""
Скрипт инициализации полной схемы ArangoDB для финансовой аналитики.
Создает коллекции (Document и Edge) и индексы согласно корпоративной модели.
"""

from arango import ArangoClient
from arango.exceptions import CollectionCreateError

# === Настройки ===
HOST = "http://localhost:8529"
USER = "root"
PASSWORD = "strongpassword"
DB_NAME = "finance_analytics"

# === Схема ===

# 1. Узлы (Document Collections)
DOCUMENT_COLLECTIONS = [
    "Companies",        # Юрлица
    "Accounts",         # Счета (51, 60, 20...)
    "CostItems",        # Статьи затрат
    "Contracts",        # Договоры
    "Projects",         # Проекты
    "BalanceSnapshots", # Снимки баланса/ОСВ
    "Dictionary",       # Справочники (категории, статусы)
    "Contacts",         # Люди (подписанты, ответственные)
    "Documents",        # Документы (сканы, тексты) для обучения ИИ
    "FinancialData",    # Сырые финансовые данные (если нужно)
    "Analytics"         # Результаты расчетов
]

# 2. Связи (Edge Collections)
EDGE_COLLECTIONS = [
    "Transactions",     # Проводки (Account -> Account)
    "Intercompany",     # Внутригрупповые связи (Company -> Company)
    "Ownership",        # Владение (Company -> Company)
    "HasContract",      # Company -> Contract
    "Incurred",         # Company -> CostItem (Понесение затрат)
    "AllocatedTo",      # Company/Transaction -> Project
    "ClassifiedAs",     # Account/CostItem -> Dictionary (Категория)
    "SignedBy",         # Contract/Transaction -> Contact
    "RelatedTo",        # Transaction -> Transaction (Цепочки)
    "Mentions"          # Document -> Company/Project/Contract (Связь документа с сущностями)
]

# 3. Индексы
INDICES = {
    "Transactions": [
        {"fields": ["date"], "name": "idx_date"},
        {"fields": ["company_id", "account_id", "period"], "name": "idx_company_account_period"},
        {"fields": ["status"], "name": "idx_status"}
    ],
    "BalanceSnapshots": [
        {"fields": ["period", "company_id"], "name": "idx_period_company"}
    ],
    "Documents": [
        {"fields": ["created_at"], "name": "idx_created_at"},
        {"fields": ["type"], "name": "idx_type"}
    ],
    "Contracts": [
        {"fields": ["number"], "name": "idx_number"},
        {"fields": ["date_start", "date_end"], "name": "idx_dates"}
    ]
}

def setup_schema():
    print(f"🚀 Настройка схемы ArangoDB: {DB_NAME}")
    
    client = ArangoClient(hosts=HOST)
    sys_db = client.db('_system', username=USER, password=PASSWORD)
    
    # Создаем базу, если нет
    if not sys_db.has_database(DB_NAME):
        sys_db.create_database(DB_NAME)
        print(f"✅ База данных {DB_NAME} создана")
    else:
        print(f"ℹ️  База данных {DB_NAME} уже существует")
        
    db = client.db(DB_NAME, username=USER, password=PASSWORD)
    
    # 1. Создаем Document Collections
    print("\n📦 Document Collections:")
    for col_name in DOCUMENT_COLLECTIONS:
        if not db.has_collection(col_name):
            db.create_collection(col_name)
            print(f"   ✅ Создана: {col_name}")
        else:
            print(f"   ℹ️  Существует: {col_name}")
            
    # 2. Создаем Edge Collections
    print("\n🔗 Edge Collections:")
    for col_name in EDGE_COLLECTIONS:
        if not db.has_collection(col_name):
            db.create_collection(col_name, edge=True)
            print(f"   ✅ Создана: {col_name}")
        else:
            # Проверяем тип
            col = db.collection(col_name)
            if not col.properties()['edge']:
                print(f"   ⚠️  ВНИМАНИЕ: {col_name} существует, но это не Edge collection!")
            else:
                print(f"   ℹ️  Существует: {col_name}")

    # 3. Создаем Индексы
    print("\n⚡ Indices:")
    for col_name, indices in INDICES.items():
        if db.has_collection(col_name):
            col = db.collection(col_name)
            existing_indices = {i['name']: i for i in col.indexes() if 'name' in i}
            
            for idx_def in indices:
                idx_name = idx_def['name']
                if idx_name not in existing_indices:
                    col.add_persistent_index(fields=idx_def['fields'], name=idx_name)
                    print(f"   ✅ Индекс {idx_name} создан в {col_name}")
                else:
                    print(f"   ℹ️  Индекс {idx_name} уже есть в {col_name}")

    print("\n🎉 Схема успешно обновлена!")

if __name__ == "__main__":
    setup_schema()
