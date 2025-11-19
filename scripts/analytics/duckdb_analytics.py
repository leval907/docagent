#!/usr/bin/env python3
"""
DuckDB Analytics & Dataset Integration
Импорт разнородных данных и поиск связей
"""

import duckdb
import os
from pathlib import Path


class DuckDBAnalytics:
    def __init__(self, db_path: str = "knowledge_base/duckdb/analytics.duckdb"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = duckdb.connect(str(self.db_path))
        self._install_extensions()
    
    def _install_extensions(self):
        """Установка расширений DuckDB"""
        print("📦 Installing DuckDB extensions...")
        
        # Для работы с разными форматами
        extensions = [
            'spatial',      # Excel, spatial data
            'json',         # JSON files
            'parquet',      # Parquet (comes by default)
            'postgres',     # PostgreSQL integration
            'httpfs',       # Read from HTTP/S3
        ]
        
        for ext in extensions:
            try:
                self.conn.execute(f"INSTALL {ext};")
                self.conn.execute(f"LOAD {ext};")
                print(f"  ✅ {ext}")
            except Exception as e:
                print(f"  ⚠️  {ext}: {e}")
    
    def import_excel(self, file_path: str, table_name: str, sheet: str = None):
        """
        Импорт Excel файла
        
        Example:
            analytics.import_excel('data.xlsx', 'sales', sheet='2024')
        """
        print(f"\n📊 Importing Excel: {file_path}")
        
        sheet_clause = f", sheet='{sheet}'" if sheet else ""
        
        query = f"""
            CREATE OR REPLACE TABLE {table_name} AS 
            SELECT * FROM st_read('{file_path}'{sheet_clause});
        """
        
        self.conn.execute(query)
        count = self.conn.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]
        print(f"  ✅ Imported {count} rows into {table_name}")
        
        # Показать структуру
        self.show_table_info(table_name)
    
    def import_csv(self, file_path: str, table_name: str, delimiter: str = ','):
        """Импорт CSV"""
        print(f"\n📊 Importing CSV: {file_path}")
        
        query = f"""
            CREATE OR REPLACE TABLE {table_name} AS 
            SELECT * FROM read_csv('{file_path}', 
                delim='{delimiter}', 
                header=true, 
                auto_detect=true
            );
        """
        
        self.conn.execute(query)
        count = self.conn.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]
        print(f"  ✅ Imported {count} rows into {table_name}")
        
        self.show_table_info(table_name)
    
    def import_json(self, file_path: str, table_name: str):
        """Импорт JSON (массив объектов)"""
        print(f"\n📊 Importing JSON: {file_path}")
        
        query = f"""
            CREATE OR REPLACE TABLE {table_name} AS 
            SELECT * FROM read_json_auto('{file_path}');
        """
        
        self.conn.execute(query)
        count = self.conn.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]
        print(f"  ✅ Imported {count} rows into {table_name}")
        
        self.show_table_info(table_name)
    
    def import_parquet(self, file_path: str, table_name: str):
        """Импорт Parquet"""
        print(f"\n📊 Importing Parquet: {file_path}")
        
        query = f"""
            CREATE OR REPLACE TABLE {table_name} AS 
            SELECT * FROM read_parquet('{file_path}');
        """
        
        self.conn.execute(query)
        count = self.conn.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]
        print(f"  ✅ Imported {count} rows into {table_name}")
        
        self.show_table_info(table_name)
    
    def connect_postgres(self, pg_url: str = None):
        """
        Подключение к PostgreSQL
        
        Example:
            analytics.connect_postgres('postgresql://user:pass@localhost/docagent')
        """
        if not pg_url:
            pg_url = "postgresql://analytics_user:analytics_secure_2025@localhost:5432/docagent"
        
        print(f"\n🔗 Connecting to PostgreSQL...")
        
        self.conn.execute(f"""
            ATTACH '{pg_url}' AS pg (TYPE POSTGRES);
        """)
        
        # Показать доступные таблицы
        tables = self.conn.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'pg'
        """).fetchall()
        
        print(f"  ✅ Connected! Available tables:")
        for table in tables:
            print(f"     - pg.{table[0]}")
    
    def show_table_info(self, table_name: str):
        """Показать структуру таблицы"""
        print(f"\n  📋 Table structure for {table_name}:")
        
        columns = self.conn.execute(f"DESCRIBE {table_name}").fetchall()
        for col in columns:
            print(f"     {col[0]:20s} {col[1]}")
    
    def list_tables(self):
        """Список всех таблиц"""
        print("\n📚 Available tables:")
        
        tables = self.conn.execute("""
            SELECT table_name, 
                   (SELECT COUNT(*) FROM information_schema.columns 
                    WHERE table_name = t.table_name) as column_count
            FROM information_schema.tables t
            WHERE table_schema = 'main'
            ORDER BY table_name
        """).fetchall()
        
        for table, cols in tables:
            count = self.conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            print(f"  📊 {table:30s} {count:>8,} rows, {cols} columns")
    
    def find_common_columns(self, table1: str, table2: str):
        """Найти общие колонки между таблицами"""
        print(f"\n🔍 Finding common columns: {table1} ↔ {table2}")
        
        result = self.conn.execute(f"""
            SELECT DISTINCT column_name
            FROM information_schema.columns
            WHERE table_name = '{table1}'
            INTERSECT
            SELECT DISTINCT column_name
            FROM information_schema.columns
            WHERE table_name = '{table2}'
        """).fetchall()
        
        if result:
            print(f"  ✅ Found {len(result)} common columns:")
            for col in result:
                print(f"     - {col[0]}")
        else:
            print(f"  ❌ No common columns found")
        
        return [r[0] for r in result]
    
    def suggest_joins(self, table1: str, table2: str):
        """Предложить возможные JOIN'ы между таблицами"""
        common_cols = self.find_common_columns(table1, table2)
        
        if not common_cols:
            print("\n💡 Trying fuzzy matching...")
            # Попробовать найти похожие колонки
            result = self.conn.execute(f"""
                WITH t1_cols AS (
                    SELECT column_name FROM information_schema.columns 
                    WHERE table_name = '{table1}'
                ),
                t2_cols AS (
                    SELECT column_name FROM information_schema.columns 
                    WHERE table_name = '{table2}'
                )
                SELECT 
                    t1.column_name as col1,
                    t2.column_name as col2,
                    levenshtein(t1.column_name, t2.column_name) as distance
                FROM t1_cols t1, t2_cols t2
                WHERE levenshtein(t1.column_name, t2.column_name) <= 3
                ORDER BY distance
                LIMIT 5
            """).fetchall()
            
            if result:
                print("\n  🎯 Potential fuzzy matches:")
                for col1, col2, dist in result:
                    print(f"     {col1} ≈ {col2} (distance: {dist})")
        else:
            print("\n💡 Suggested JOIN queries:")
            for col in common_cols:
                print(f"""
    SELECT *
    FROM {table1} t1
    JOIN {table2} t2 ON t1.{col} = t2.{col}
    LIMIT 10;
                """)
    
    def analyze_relationships(self):
        """Анализ связей между всеми таблицами"""
        print("\n🔍 Analyzing relationships between tables...")
        
        tables = self.conn.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'main'
        """).fetchall()
        
        tables = [t[0] for t in tables]
        
        print(f"\n📊 Found {len(tables)} tables")
        
        relationships = []
        for i, t1 in enumerate(tables):
            for t2 in tables[i+1:]:
                common = self.find_common_columns(t1, t2)
                if common:
                    relationships.append((t1, t2, common))
        
        if relationships:
            print(f"\n✅ Found {len(relationships)} potential relationships:")
            for t1, t2, cols in relationships:
                print(f"\n  {t1} ↔ {t2}")
                print(f"    Common columns: {', '.join(cols)}")
        else:
            print("\n❌ No direct relationships found")
    
    def query(self, sql: str):
        """Выполнить произвольный SQL запрос"""
        print(f"\n🔍 Executing query:")
        print(f"   {sql[:100]}...")
        
        result = self.conn.execute(sql).fetchall()
        
        # Получить имена колонок
        description = self.conn.description
        if description:
            cols = [d[0] for d in description]
            print(f"\n  📊 Results ({len(result)} rows):")
            
            # Показать первые 10 строк
            for row in result[:10]:
                print("  ", dict(zip(cols, row)))
        
        return result
    
    def export_to_excel(self, query: str, output_file: str):
        """Экспорт результата запроса в Excel"""
        print(f"\n📤 Exporting to Excel: {output_file}")
        
        self.conn.execute(f"""
            COPY ({query}) 
            TO '{output_file}' 
            WITH (FORMAT GDAL, DRIVER 'XLSX');
        """)
        
        print(f"  ✅ Exported to {output_file}")
    
    def close(self):
        """Закрыть соединение"""
        self.conn.close()


def main():
    """Пример использования"""
    
    analytics = DuckDBAnalytics()
    
    print("""
╔══════════════════════════════════════════════════════════╗
║  DuckDB Analytics - Dataset Integration                  ║
╚══════════════════════════════════════════════════════════╝

Available commands:
  analytics.import_excel('file.xlsx', 'table_name')
  analytics.import_csv('file.csv', 'table_name')
  analytics.import_json('file.json', 'table_name')
  analytics.list_tables()
  analytics.find_common_columns('table1', 'table2')
  analytics.suggest_joins('table1', 'table2')
  analytics.analyze_relationships()
  analytics.query("SELECT * FROM table LIMIT 10")
  analytics.export_to_excel("SELECT * FROM table", 'output.xlsx')
  analytics.connect_postgres()  # Подключить PostgreSQL

Example workflow:
  1. Import multiple Excel/CSV files
  2. Use analyze_relationships() to find connections
  3. Create JOIN queries based on suggestions
  4. Export results to Excel for reporting
    """)
    
    # Пример автоматического анализа если есть файлы
    kb_dir = Path("knowledge_base/duckdb")
    if kb_dir.exists():
        print("\n🔍 Scanning knowledge_base/duckdb/ for data files...")
        
        # Автоматически импортировать найденные файлы
        for file in kb_dir.glob("*.csv"):
            table_name = file.stem.replace('-', '_').replace(' ', '_')
            try:
                analytics.import_csv(str(file), table_name)
            except Exception as e:
                print(f"  ⚠️  Failed to import {file.name}: {e}")
        
        for file in kb_dir.glob("*.json"):
            table_name = file.stem.replace('-', '_').replace(' ', '_')
            try:
                analytics.import_json(str(file), table_name)
            except Exception as e:
                print(f"  ⚠️  Failed to import {file.name}: {e}")
        
        # Показать что загружено
        analytics.list_tables()
        
        # Анализ связей
        analytics.analyze_relationships()
    
    return analytics


if __name__ == "__main__":
    analytics = main()
    
    # Оставить интерактивную сессию
    print("\n💡 DuckDB analytics object is available as 'analytics'")
    print("   Type: help(analytics) for more info")
