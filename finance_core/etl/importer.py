import pandas as pd
import duckdb
from typing import List
from finance_core.db.connector import DBManager

class DuckDBImporter:
    """
    Класс для импорта данных в DuckDB.
    """
    
    def __init__(self):
        self.db_manager = DBManager()

    def import_revenue_data(self, df: pd.DataFrame, table_name: str = "revenue_raw"):
        """
        Импортирует DataFrame с выручкой в указанную таблицу DuckDB.
        """
        if df is None or df.empty:
            print("⚠️ Нет данных для импорта")
            return

        conn = self.db_manager.get_duckdb_conn()
        try:
            print(f"📊 Загрузка {len(df)} строк в таблицу '{table_name}'...")
            
            # Удаляем старую таблицу и создаем новую
            conn.execute(f"DROP TABLE IF EXISTS {table_name}")
            conn.execute(f"CREATE TABLE {table_name} AS SELECT * FROM df")
            
            # Проверка
            count = conn.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]
            print(f"✅ Успешно загружено: {count} строк")
            
        except Exception as e:
            print(f"❌ Ошибка при импорте в DuckDB: {e}")
        finally:
            conn.close()

    def import_group_companies(self, companies: List[str], table_name: str = "group_companies"):
        """
        Импортирует список компаний группы.
        """
        if not companies:
            return

        df = pd.DataFrame({'company_name': companies})
        conn = self.db_manager.get_duckdb_conn()
        try:
            conn.execute(f"DROP TABLE IF EXISTS {table_name}")
            conn.execute(f"CREATE TABLE {table_name} AS SELECT * FROM df")
            print(f"✅ Список компаний группы обновлен ({len(companies)} записей)")
        except Exception as e:
            print(f"❌ Ошибка при импорте компаний: {e}")
        finally:
            conn.close()
