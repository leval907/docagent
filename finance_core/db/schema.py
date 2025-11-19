from finance_core.db.connector import DBManager

class SchemaManager:
    def __init__(self):
        self.db_manager = DBManager()
        self.db = self.db_manager.get_arango_db()

    def init_schema(self):
        """Initializes the database schema with all required collections."""
        print(f"🛠 Initializing schema in database: {self.db.name}")
        
        # 1. Document Collections (Vertices)
        doc_collections = [
            "Companies",    # Юрлица
            "Accounts",     # План счетов
            "CostItems",    # Статьи затрат/ДДС
            "Contracts",    # Договоры
            "Projects",     # Проекты
            "BalanceSnapshots", # Снапшоты баланса
            "Dictionary",   # Финансовый словарь
            "FinancialData", # Финансовые данные (P&L + Balance Sheet)
            "Analytics"     # Аналитические показатели
        ]
        
        for col_name in doc_collections:
            if not self.db.has_collection(col_name):
                print(f"   + Creating collection: {col_name}")
                self.db.create_collection(col_name)
            else:
                print(f"   . Collection exists: {col_name}")

        # 2. Edge Collections (Relations)
        edge_collections = [
            "Transactions", # Проводки / Платежи
            "ClassifiedAs", # Классификация (опционально)
            "SignedBy",     # Подписанты договоров
            "AllocatedTo",  # Привязка к проектам
            "Ownership"     # Структура владения
        ]
        
        for col_name in edge_collections:
            if not self.db.has_collection(col_name):
                print(f"   + Creating edge collection: {col_name}")
                self.db.create_collection(col_name, edge=True)
            else:
                print(f"   . Edge collection exists: {col_name}")

        print("✅ Schema initialization complete.")

    def reset_db(self):
        """Drops and recreates the database (Use with caution!)."""
        # Note: This requires system DB access which DBManager handles internally for creation,
        # but for dropping we might need to be careful. 
        # For now, we'll just truncate collections.
        print("⚠️ Resetting database data...")
        for col in self.db.collections():
            if not col['system']:
                print(f"   - Truncating {col['name']}")
                self.db.collection(col['name']).truncate()
        print("✅ Database reset complete.")

if __name__ == "__main__":
    schema = SchemaManager()
    schema.init_schema()
