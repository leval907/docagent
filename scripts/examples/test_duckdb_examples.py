#!/usr/bin/env python3
"""
Пример работы с DuckDB Analytics
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.duckdb_analytics import DuckDBAnalytics


def example_basic_queries():
    """Базовые запросы"""
    print("\n" + "="*60)
    print("📊 EXAMPLE 1: Basic Queries")
    print("="*60)
    
    analytics = DuckDBAnalytics()
    
    # Импорт тестовых данных
    analytics.import_csv('knowledge_base/duckdb/products.csv', 'products')
    analytics.import_json('knowledge_base/duckdb/sales.json', 'sales')
    
    # Простой запрос
    print("\n1️⃣ All products:")
    analytics.query("SELECT * FROM products")
    
    print("\n2️⃣ All sales:")
    analytics.query("SELECT * FROM sales")
    
    return analytics


def example_joins():
    """Примеры JOIN'ов"""
    print("\n" + "="*60)
    print("🔗 EXAMPLE 2: Finding Relationships with JOINs")
    print("="*60)
    
    analytics = DuckDBAnalytics()
    analytics.import_csv('knowledge_base/duckdb/products.csv', 'products')
    analytics.import_json('knowledge_base/duckdb/sales.json', 'sales')
    
    # Найти связи
    print("\n🔍 Suggesting JOIN strategies:")
    analytics.suggest_joins('products', 'sales')
    
    # Правильный JOIN через product_id
    print("\n3️⃣ Sales with product details (correct JOIN):")
    analytics.query("""
        SELECT 
            s.id as sale_id,
            s.customer,
            s.quantity,
            s.date,
            p.name as product_name,
            p.category,
            p.price,
            s.quantity * p.price as total_amount
        FROM sales s
        JOIN products p ON s.product_id = p.id
        ORDER BY s.date
    """)
    
    # Агрегация
    print("\n4️⃣ Sales summary by product:")
    analytics.query("""
        SELECT 
            p.name as product_name,
            COUNT(s.id) as num_sales,
            SUM(s.quantity) as total_quantity,
            SUM(s.quantity * p.price) as total_revenue
        FROM sales s
        JOIN products p ON s.product_id = p.id
        GROUP BY p.name
        ORDER BY total_revenue DESC
    """)
    
    # Топ клиенты
    print("\n5️⃣ Top customers by revenue:")
    analytics.query("""
        SELECT 
            s.customer,
            COUNT(DISTINCT s.id) as num_purchases,
            SUM(s.quantity * p.price) as total_spent
        FROM sales s
        JOIN products p ON s.product_id = p.id
        GROUP BY s.customer
        ORDER BY total_spent DESC
    """)
    
    return analytics


def example_postgres_integration():
    """Интеграция с PostgreSQL"""
    print("\n" + "="*60)
    print("🔗 EXAMPLE 3: PostgreSQL Integration")
    print("="*60)
    
    analytics = DuckDBAnalytics()
    
    try:
        # Подключиться к PostgreSQL
        analytics.connect_postgres(
            'postgresql://analytics_user:analytics_secure_2025@localhost:5432/docagent'
        )
        
        print("\n6️⃣ Documents from PostgreSQL:")
        analytics.query("""
            SELECT 
                id, 
                app_name, 
                LEFT(url, 50) as url_preview, 
                word_count
            FROM pg.documents 
            LIMIT 5
        """)
        
        # Анализ документов по приложениям
        print("\n7️⃣ Documents statistics by app:")
        analytics.query("""
            SELECT 
                app_name,
                COUNT(*) as doc_count,
                SUM(word_count) as total_words,
                AVG(word_count) as avg_words
            FROM pg.documents
            GROUP BY app_name
            ORDER BY doc_count DESC
        """)
        
    except Exception as e:
        print(f"⚠️  PostgreSQL not available: {e}")
        print("   (This is expected if PostgreSQL is not running)")
    
    return analytics


def example_export():
    """Экспорт в разные форматы"""
    print("\n" + "="*60)
    print("📤 EXAMPLE 4: Export to Different Formats")
    print("="*60)
    
    analytics = DuckDBAnalytics()
    analytics.import_csv('knowledge_base/duckdb/products.csv', 'products')
    analytics.import_json('knowledge_base/duckdb/sales.json', 'sales')
    
    # Создать сводный отчёт
    report_query = """
        SELECT 
            p.category,
            p.name as product_name,
            COUNT(s.id) as sales_count,
            SUM(s.quantity) as total_units_sold,
            SUM(s.quantity * p.price) as revenue
        FROM products p
        LEFT JOIN sales s ON p.id = s.product_id
        GROUP BY p.category, p.name
        ORDER BY revenue DESC
    """
    
    print("\n8️⃣ Sales report:")
    analytics.query(report_query)
    
    # Экспорт в Parquet (сжатый формат)
    print("\n📦 Exporting to Parquet...")
    analytics.conn.execute(f"""
        COPY ({report_query}) 
        TO 'knowledge_base/duckdb/sales_report.parquet' 
        (FORMAT PARQUET, COMPRESSION ZSTD)
    """)
    print("  ✅ Exported to sales_report.parquet")
    
    # Экспорт в CSV
    print("\n📄 Exporting to CSV...")
    analytics.conn.execute(f"""
        COPY ({report_query}) 
        TO 'knowledge_base/duckdb/sales_report.csv' 
        (HEADER, DELIMITER ',')
    """)
    print("  ✅ Exported to sales_report.csv")
    
    # Экспорт в JSON
    print("\n🔗 Exporting to JSON...")
    analytics.conn.execute(f"""
        COPY ({report_query}) 
        TO 'knowledge_base/duckdb/sales_report.json'
    """)
    print("  ✅ Exported to sales_report.json")
    
    print("\n📂 Generated files:")
    import os
    for file in os.listdir('knowledge_base/duckdb/'):
        if 'sales_report' in file:
            size = os.path.getsize(f'knowledge_base/duckdb/{file}')
            print(f"  - {file:30s} {size:>8,} bytes")
    
    return analytics


def main():
    """Запустить все примеры"""
    print("""
╔══════════════════════════════════════════════════════════╗
║        DuckDB Analytics - Interactive Examples           ║
╚══════════════════════════════════════════════════════════╝
    """)
    
    # Запустить примеры
    example_basic_queries()
    example_joins()
    example_postgres_integration()
    example_export()
    
    print("\n" + "="*60)
    print("✅ All examples completed!")
    print("="*60)
    
    print("""
💡 Next steps:
  1. Import your own Excel/CSV files
  2. Use analyze_relationships() to find connections
  3. Create custom queries to explore data
  4. Export results for reporting

Try:
  python -i scripts/test_duckdb_examples.py
  >>> analytics = DuckDBAnalytics()
  >>> analytics.list_tables()
    """)


if __name__ == "__main__":
    main()
