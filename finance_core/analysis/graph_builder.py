import pandas as pd
from finance_core.db.connector import DBManager
from arango.database import StandardDatabase

class GraphBuilder:
    """
    Класс для построения графа транзакций в ArangoDB.
    """
    
    def __init__(self):
        self.db_manager = DBManager()
        self.db: StandardDatabase = self.db_manager.get_arango_db()
        self._setup_collections()

    def _setup_collections(self):
        """Создает необходимые коллекции в ArangoDB"""
        # Вершины: Компании
        if not self.db.has_collection('Companies'):
            self.db.create_collection('Companies')
        
        # Ребра: Транзакции (Платежи)
        if not self.db.has_collection('Transactions'):
            self.db.create_collection('Transactions', edge=True)

    def build_graph_from_duckdb(self):
        """
        Строит граф на основе данных из DuckDB.
        """
        conn = self.db_manager.get_duckdb_conn()
        try:
            print("📊 Построение графа транзакций...")
            
            # 1. Получаем список всех уникальных компаний (наши компании + контрагенты)
            # Наши компании
            our_companies = conn.execute('SELECT DISTINCT "Компания" FROM revenue_raw').fetchdf()['Компания'].tolist()
            
            # Контрагенты
            counterparties = conn.execute('SELECT DISTINCT "Контрагент" FROM revenue_raw').fetchdf()['Контрагент'].tolist()
            
            all_entities = set(our_companies + counterparties)
            
            # 2. Загружаем вершины (Companies)
            companies_coll = self.db.collection('Companies')
            
            # Очищаем старые данные (опционально, для полной перестройки)
            companies_coll.truncate()
            
            print(f"   - Загрузка {len(all_entities)} компаний...")
            
            batch = []
            for entity in all_entities:
                # Нормализуем ключ (ArangoDB _key должен быть безопасным строковым значением)
                key = self._normalize_key(entity)
                doc = {
                    '_key': key,
                    'name': entity,
                    'is_group_member': entity in our_companies
                }
                batch.append(doc)
                
                if len(batch) >= 1000:
                    companies_coll.import_bulk(batch, on_duplicate='update')
                    batch = []
            
            if batch:
                companies_coll.import_bulk(batch, on_duplicate='update')

            # 3. Загружаем ребра (Transactions)
            transactions_coll = self.db.collection('Transactions')
            transactions_coll.truncate()
            
            # Выбираем транзакции оплаты (51_62) - деньги пришли ОТ контрагента К нам
            # Дт51 Кт62: Мы (Компания) получили деньги от Контрагента
            # Значит поток денег: Контрагент -> Компания
            
            query = """
            SELECT 
                "Компания", 
                "Контрагент", 
                SUM("51_62") as amount,
                COUNT(*) as count
            FROM revenue_raw 
            WHERE "51_62" > 0 
            GROUP BY "Компания", "Контрагент"
            """
            
            transactions = conn.execute(query).fetchdf()
            print(f"   - Загрузка {len(transactions)} связей (платежей)...")
            
            edge_batch = []
            for _, row in transactions.iterrows():
                from_key = self._normalize_key(row['Контрагент'])
                to_key = self._normalize_key(row['Компания'])
                
                edge = {
                    '_from': f'Companies/{from_key}',
                    '_to': f'Companies/{to_key}',
                    'amount': row['amount'],
                    'count': row['count'],
                    'type': 'payment_received'
                }
                edge_batch.append(edge)
                
                if len(edge_batch) >= 1000:
                    transactions_coll.import_bulk(edge_batch, on_duplicate='ignore')
                    edge_batch = []
            
            if edge_batch:
                transactions_coll.import_bulk(edge_batch, on_duplicate='ignore')
                
            print("✅ Граф успешно построен!")
            
        except Exception as e:
            print(f"❌ Ошибка при построении графа: {e}")
        finally:
            conn.close()

    def _normalize_key(self, text: str) -> str:
        """Создает безопасный ключ для ArangoDB из названия"""
        import hashlib
        # Используем MD5 хеш для гарантии валидности ключа
        return hashlib.md5(text.encode('utf-8')).hexdigest()
