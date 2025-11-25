
import psycopg2
import pandas as pd
import sys

# Connection parameters
DB_PARAMS = {
    "host": "localhost",
    "port": 5432,
    "database": "analytics",
    "user": "analytics_user",
    "password": "analytics_secure_2025"
}

def get_db_connection():
    try:
        conn = psycopg2.connect(**DB_PARAMS)
        return conn
    except Exception as e:
        print(f"Error connecting to database: {e}")
        sys.exit(1)

def list_tables():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT table_schema, table_name 
        FROM information_schema.tables 
        WHERE table_schema IN ('public', 'history', 'analytics', 'staging')
        ORDER BY table_schema, table_name;
    """)
    tables = cursor.fetchall()
    print("\n--- Available Tables ---")
    for schema, table in tables:
        print(f"{schema}.{table}")
    conn.close()

if __name__ == "__main__":
    list_tables()
