
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

def analyze_pnl_and_costs():
    conn = get_db_connection()
    
    print("--- P&L Summary (analytics.profit_loss_9m) ---")
    # Check columns first
    query_cols = "SELECT * FROM analytics.profit_loss_9m LIMIT 0;"
    cursor = conn.cursor()
    cursor.execute(query_cols)
    colnames = [desc[0] for desc in cursor.description]
    print(f"Columns: {colnames}")
    
    query_pnl = """
    SELECT *
    FROM analytics.profit_loss_9m 
    ORDER BY revenue DESC;
    """
    df_pnl = pd.read_sql_query(query_pnl, conn)
    print(df_pnl.to_string())
    
    print("\n--- Cost Structure (analytics.fct_cost_structure_by_company) ---")
    
    # Get aggregated costs by company and cost group
    query_costs = """
    SELECT 
        company_name, 
        category_name,
        group_name, 
        SUM(net_amount) as total_amount 
    FROM analytics.fct_cost_structure_by_company 
    GROUP BY company_name, category_name, group_name 
    ORDER BY company_name, total_amount DESC;
    """
    df_costs = pd.read_sql_query(query_costs, conn)
    
    # Print per company
    companies = df_costs['company_name'].unique()
    for company in companies:
        print(f"\n>>> {company}")
        company_costs = df_costs[df_costs['company_name'] == company]
        print(company_costs[['category_name', 'group_name', 'total_amount']].to_string(index=False))
    
    conn.close()

if __name__ == "__main__":
    analyze_pnl_and_costs()
