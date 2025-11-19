import pandas as pd
import re
from finance_core.db.connector import DBManager

class DictionaryLoader:
    def __init__(self):
        self.db_manager = DBManager()
        self.db = self.db_manager.get_arango_db()

    def _sanitize_key(self, key: str) -> str:
        """Очищает ключ для ArangoDB (MD5 хеш для длинных или русских строк)"""
        import hashlib
        return hashlib.md5(key.encode('utf-8')).hexdigest()

    def load_from_excel(self, file_path: str):
        """Загружает словарь из Excel в ArangoDB"""
        print(f"📂 Чтение файла: {file_path}")
        # Читаем без заголовка, так как структура специфичная
        df = pd.read_excel(file_path, header=None)
        
        # Ожидаем, что в колонке 1 - Термин, в колонке 2 - Определение
        # Удаляем строки, где нет термина
        df = df.dropna(subset=[1])
        
        dict_coll = self.db.collection('Dictionary')
        dict_coll.truncate()
        
        batch = []
        for _, row in df.iterrows():
            term = str(row[1]).strip()
            definition = str(row[2]).strip() if pd.notna(row[2]) else ""
            
            if not term or term.lower() == 'nan':
                continue
                
            key = self._sanitize_key(term)
            
            doc = {
                '_key': key,
                'term': term,
                'definition': definition
            }
            batch.append(doc)
            
            if len(batch) >= 1000:
                dict_coll.import_bulk(batch, on_duplicate='replace')
                batch = []
        
        if batch:
            dict_coll.import_bulk(batch, on_duplicate='replace')
            
        print(f"✅ Загружено {dict_coll.count()} терминов в словарь.")

    def link_terms_to_accounts(self):
        """Создает связи между Терминами и Счетами (по совпадению названий)"""
        print("🔗 Создание связей Dictionary -> Accounts...")
        
        if not self.db.has_collection('RelatedTo'):
            self.db.create_collection('RelatedTo', edge=True)
            
        related_coll = self.db.collection('RelatedTo')
        related_coll.truncate()
        
        # Получаем все счета
        accounts = list(self.db.collection('Accounts').all())
        # Получаем все термины
        terms = list(self.db.collection('Dictionary').all())
        
        edges = []
        for term in terms:
            term_str = term['term'].lower()
            
            for acc in accounts:
                acc_name = acc['name'].lower()
                
                # Простая эвристика: если термин содержится в названии счета или наоборот
                # Или если есть сильное пересечение слов
                if term_str == acc_name or term_str in acc_name:
                    edge = {
                        '_from': term['_id'],
                        '_to': acc['_id'],
                        'type': 'defines_account'
                    }
                    edges.append(edge)
        
        if edges:
            related_coll.import_bulk(edges, on_duplicate='ignore')
            print(f"✅ Создано {len(edges)} связей между словарем и счетами.")

if __name__ == "__main__":
    loader = DictionaryLoader()
    loader.load_from_excel('/opt/docagent/docs/a-findocs/Словарь.xlsx')
    loader.link_terms_to_accounts()
