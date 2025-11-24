import psycopg2
from psycopg2 import sql
import sys

# Admin credentials from README/Docker
ADMIN_USER = "docagent"
ADMIN_PASS = "docagent123"
DB_NAME = "analytics"
DB_HOST = "localhost"

# Target credentials
TARGET_USER = "analytics_user"
TARGET_PASS = "analytics_secure_2025"

def setup_database():
    # 1. Connect as Admin to create user and schema if needed
    try:
        conn = psycopg2.connect(
            host=DB_HOST,
            dbname=DB_NAME,
            user=ADMIN_USER,
            password=ADMIN_PASS
        )
        conn.autocommit = True
        cur = conn.cursor()
        
        # Create User if not exists
        try:
            cur.execute(sql.SQL("CREATE USER {} WITH PASSWORD %s").format(sql.Identifier(TARGET_USER)), (TARGET_PASS,))
            print(f"User {TARGET_USER} created.")
        except psycopg2.errors.DuplicateObject:
            print(f"User {TARGET_USER} already exists.")
        
        # Create Schema 'analytics'
        cur.execute("CREATE SCHEMA IF NOT EXISTS analytics AUTHORIZATION {};".format(TARGET_USER))
        print("Schema 'analytics' ensured.")
        
        # Grant usage just in case
        cur.execute("GRANT ALL ON SCHEMA analytics TO {};".format(TARGET_USER))
        
        cur.close()
        conn.close()
        
    except Exception as e:
        print(f"Admin connection failed or setup error: {e}")
        # If admin fails, maybe we can just connect with the target user directly (if it already exists)
        pass

    # 2. Connect as the specific user to create the table
    print(f"Connecting as {TARGET_USER}...")
    try:
        conn = psycopg2.connect(
            host=DB_HOST,
            dbname=DB_NAME,
            user=TARGET_USER,
            password=TARGET_PASS
        )
        conn.autocommit = True
        cur = conn.cursor()
        
        # Create Table
        # Note: We use double quotes for column names with spaces/special chars
        create_table_sql = """
        CREATE TABLE IF NOT EXISTS analytics.profit_v (
            id SERIAL PRIMARY KEY,
            company_code VARCHAR(50),
            company_name VARCHAR(255),
            "Revenue" DECIMAL(18, 2),
            "Cost of Goods" DECIMAL(18, 2),
            "Overheads" DECIMAL(18, 2),
            "Leasing" DECIMAL(18, 2),
            "Extraordinary Income/Expenses" DECIMAL(18, 2),
            "Interest Paid" DECIMAL(18, 2),
            "Depreciation & Amortisation" DECIMAL(18, 2),
            "Tax Paid" DECIMAL(18, 2),
            "Dividends Paid" DECIMAL(18, 2)
        );
        """
        cur.execute(create_table_sql)
        print("Table analytics.profit_v created.")

        # Add Comments (Russian translations)
        comments = {
            "Revenue": "Выручка",
            "Cost of Goods": "Себестоимость",
            "Overheads": "Накладные расходы",
            "Leasing": "Лизинг",
            "Extraordinary Income/Expenses": "Прочие доходы/расходы",
            "Interest Paid": "Проценты к уплате",
            "Depreciation & Amortisation": "Амортизация",
            "Tax Paid": "Налоги",
            "Dividends Paid": "Дивиденды",
            "company_code": "Код компании",
            "company_name": "Название компании",
            "id": "Идентификатор"
        }

        for col, comment in comments.items():
            # Always quote column names to handle case sensitivity and special characters
            col_ident = f'"{col}"'
            
            query = f"COMMENT ON COLUMN analytics.profit_v.{col_ident} IS %s;"
            cur.execute(query, (comment,))
            
        print("Comments added successfully.")
        
        cur.close()
        conn.close()
        
    except Exception as e:
        print(f"Failed to create table as {TARGET_USER}: {e}")
        sys.exit(1)

if __name__ == "__main__":
    setup_database()
