import psycopg2
import sys

DB_CONFIG = {
    'host': 'localhost',
    'database': 'analytics',
    'user': 'analytics_user',
    'password': 'analytics_secure_2025',
    'port': '5432'
}

def check_connection():
    print(f"Connecting to {DB_CONFIG['database']} as {DB_CONFIG['user']}...")
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        cur.execute("SELECT version();")
        version = cur.fetchone()[0]
        print(f"Connected successfully!")
        print(f"PostgreSQL Version: {version}")
        
        cur.execute("SELECT current_database(), current_user;")
        db, user = cur.fetchone()
        print(f"Database: {db}, User: {user}")
        
        cur.close()
        conn.close()
        return True
    except Exception as e:
        print(f"Connection failed: {e}")
        return False

if __name__ == "__main__":
    if check_connection():
        sys.exit(0)
    else:
        sys.exit(1)
