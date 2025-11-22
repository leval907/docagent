import duckdb
import psycopg2
import pandas as pd
from datetime import datetime
import sys
import os

# Add project root to path to import config
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

from finance_core.config import DUCKDB_PATH, POSTGRES_HOST, POSTGRES_PORT, POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_DB

def get_postgres_conn():
    return psycopg2.connect(
        host=POSTGRES_HOST,
        port=POSTGRES_PORT,
        user=POSTGRES_USER,
        password=POSTGRES_PASSWORD,
        database=POSTGRES_DB
    )

def migrate_companies(duck_con, pg_conn):
    print("\n[1] Migrating Companies...")
    cur = pg_conn.cursor()
    
    # Extract unique companies from group_companies table
    try:
        companies_df = duck_con.execute("SELECT DISTINCT company_name FROM group_companies").fetchdf()
    except:
        # Fallback if group_companies doesn't exist or is empty, try osv_general
        print("  Note: group_companies table not found/empty, using osv_general")
        companies_df = duck_con.execute("SELECT DISTINCT company_raw as company_name FROM osv_general").fetchdf()
    
    count = 0
    for _, row in companies_df.iterrows():
        company_name = row['company_name']
        if not company_name: continue
        
        # Generate a code (e.g., "GROSS_GROUP_M")
        company_code = company_name.strip().upper().replace(' ', '_').replace('"', '').replace("'", "")
        # Truncate to 50 chars just in case
        company_code = company_code[:50]
        
        try:
            cur.execute("""
                INSERT INTO master.companies (company_code, company_name)
                VALUES (%s, %s)
                ON CONFLICT (company_code) DO NOTHING
            """, (company_code, company_name.strip()))
            count += 1
        except Exception as e:
            print(f"  Error inserting {company_name}: {e}")
            pg_conn.rollback()
            continue
            
    pg_conn.commit()
    cur.close()
    print(f"  ✓ Processed {count} companies")

def migrate_accounts(duck_con, pg_conn):
    print("\n[2] Migrating Chart of Accounts...")
    cur = pg_conn.cursor()
    
    # Extract unique accounts from osv_general
    accounts_df = duck_con.execute("SELECT DISTINCT account FROM osv_general").fetchdf()
    
    count = 0
    for _, row in accounts_df.iterrows():
        account_code = str(row['account'])
        account_name = f"Account {account_code}" 
        
        # Determine type based on code
        acc_type = 'ASSET'
        if account_code.startswith('6') or account_code.startswith('7'):
            acc_type = 'LIABILITY'
        elif account_code.startswith('9'):
            acc_type = 'INCOME'
            
        try:
            cur.execute("""
                INSERT INTO master.chart_of_accounts (account_code, account_name, account_type)
                VALUES (%s, %s, %s)
                ON CONFLICT (account_code) DO NOTHING
            """, (account_code, account_name, acc_type))
            count += 1
        except Exception as e:
            print(f"  Error inserting {account_code}: {e}")
            pg_conn.rollback()
            continue
            
    pg_conn.commit()
    cur.close()
    print(f"  ✓ Processed {count} accounts")

def parse_period(period_str):
    # Handle "9_months_2025" -> 2025-09-30
    if '9_months_2025' in period_str:
        return '2025-09-30'
    if '2025-H1' in period_str:
        return '2025-06-30'
    return '2025-01-01'

def migrate_balances(duck_con, pg_conn):
    print("\n[3] Migrating OSV Balances (from osv_general)...")
    cur = pg_conn.cursor()
    
    # Get data from osv_general
    query = """
    SELECT 
        company_raw as company_name,
        period,
        account,
        SUM(initial_balance_dt) as debit_begin,
        SUM(initial_balance_kt) as credit_begin,
        SUM(turnover_dt) as debit_turnover,
        SUM(turnover_kt) as credit_turnover,
        SUM(final_balance_dt) as debit_end,
        SUM(final_balance_kt) as credit_end
    FROM osv_general
    GROUP BY company_raw, period, account
    """
    
    df = duck_con.execute(query).fetchdf()
    print(f"  Found {len(df)} aggregated records")
    
    # Cache company ids
    cur.execute("SELECT company_name, id FROM master.companies")
    company_map = {row[0]: row[1] for row in cur.fetchall()}
    
    inserted = 0
    for _, row in df.iterrows():
        c_name = row['company_name'].strip() if row['company_name'] else ""
        company_id = company_map.get(c_name)
        
        if not company_id:
            # Try fuzzy match or skip
            # print(f"  Warning: Company ID not found for '{c_name}'")
            continue
            
        period_date = parse_period(row['period'])
        
        try:
            cur.execute("""
                INSERT INTO history.osv_balances 
                (company_id, period_date, account_code, 
                 debit_begin, credit_begin, debit_turnover, credit_turnover, debit_end, credit_end)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (company_id, period_date, account_code) 
                DO UPDATE SET
                    debit_begin = EXCLUDED.debit_begin,
                    credit_begin = EXCLUDED.credit_begin,
                    debit_turnover = EXCLUDED.debit_turnover,
                    credit_turnover = EXCLUDED.credit_turnover,
                    debit_end = EXCLUDED.debit_end,
                    credit_end = EXCLUDED.credit_end,
                    loaded_at = NOW()
            """, (
                company_id, period_date, str(row['account']),
                row['debit_begin'], row['credit_begin'], 
                row['debit_turnover'], row['credit_turnover'], 
                row['debit_end'], row['credit_end']
            ))
            inserted += 1
        except Exception as e:
            print(f"  Error inserting balance: {e}")
            pg_conn.rollback()
            
    pg_conn.commit()
    cur.close()
    print(f"  ✓ Inserted/Updated {inserted} balance records")

def migrate_client_turnovers(duck_con, pg_conn):
    print("\n[4] Migrating Client Turnovers (60/62)...")
    cur = pg_conn.cursor()
    
    # Cache company ids
    cur.execute("SELECT company_name, id FROM master.companies")
    company_map = {row[0]: row[1] for row in cur.fetchall()}
    
    for table in ['osv_60', 'osv_62']:
        print(f"  Processing {table}...")
        query = f"""
        SELECT 
            company_raw as company_name,
            period,
            account_type as account_code,
            counterparty,
            SUM(initial_balance_dt) as debit_begin,
            SUM(initial_balance_kt) as credit_begin,
            SUM(turnover_dt) as debit_turnover,
            SUM(turnover_kt) as credit_turnover,
            SUM(final_balance_dt) as debit_end,
            SUM(final_balance_kt) as credit_end
        FROM {table}
        GROUP BY company_raw, period, account_type, counterparty
        """
        
        df = duck_con.execute(query).fetchdf()
        
        inserted = 0
        for _, row in df.iterrows():
            c_name = row['company_name'].strip() if row['company_name'] else ""
            company_id = company_map.get(c_name)
            if not company_id: continue
                
            period_date = parse_period(row['period'])
            counterparty = row['counterparty'][:50] if row['counterparty'] else "Unknown" # Truncate for code
            
            # Ensure counterparty exists in master
            # (Simplified: we just use the name as code for now)
            try:
                cur.execute("""
                    INSERT INTO master.counterparties (counterparty_code, counterparty_name)
                    VALUES (%s, %s)
                    ON CONFLICT (counterparty_code) DO NOTHING
                """, (counterparty, row['counterparty']))
            except:
                pg_conn.rollback()

            try:
                cur.execute("""
                    INSERT INTO history.client_turnovers
                    (company_id, period_date, account_code, counterparty_code,
                     debit_begin, credit_begin, debit_turnover, credit_turnover, debit_end, credit_end)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (company_id, period_date, account_code, counterparty_code, contract_number) 
                    DO NOTHING
                """, (
                    company_id, period_date, str(row['account_code']), counterparty,
                    row['debit_begin'], row['credit_begin'], 
                    row['debit_turnover'], row['credit_turnover'], 
                    row['debit_end'], row['credit_end']
                ))
                inserted += 1
            except Exception as e:
                # print(f"  Error inserting client turnover: {e}")
                pg_conn.rollback()
        
        pg_conn.commit()
        print(f"    ✓ Inserted {inserted} records from {table}")
    
    cur.close()

def main():
    print("Starting Migration: DuckDB -> PostgreSQL")
    
    # Connect to DuckDB
    try:
        duck_con = duckdb.connect(str(DUCKDB_PATH), read_only=True)
        print("✓ Connected to DuckDB")
    except Exception as e:
        print(f"✗ Failed to connect to DuckDB: {e}")
        return

    # Connect to Postgres
    try:
        pg_conn = get_postgres_conn()
        print("✓ Connected to PostgreSQL")
    except Exception as e:
        print(f"✗ Failed to connect to PostgreSQL: {e}")
        return

    try:
        migrate_companies(duck_con, pg_conn)
        migrate_accounts(duck_con, pg_conn)
        migrate_balances(duck_con, pg_conn)
        migrate_client_turnovers(duck_con, pg_conn)
        print("\nMigration Completed Successfully!")
    except Exception as e:
        print(f"\nMigration Failed: {e}")
    finally:
        duck_con.close()
        pg_conn.close()

if __name__ == "__main__":
    main()
