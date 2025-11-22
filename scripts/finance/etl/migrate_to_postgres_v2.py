#!/usr/bin/env python3
"""
Миграция данных из DuckDB в PostgreSQL
Основано на FINAL_DECISION.md и postgresql_schema_for_duckdb.sql
"""

import duckdb
import psycopg2
from psycopg2.extras import execute_batch
from pathlib import Path
import sys
from datetime import datetime
import re
import unidecode

# Добавим путь к finance_core
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from finance_core.config import (
    DUCKDB_PATH,
    POSTGRES_HOST, POSTGRES_PORT, POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_DB
)

POSTGRES_CONFIG = {
    'host': POSTGRES_HOST,
    'port': POSTGRES_PORT,
    'user': POSTGRES_USER,
    'password': POSTGRES_PASSWORD,
    'dbname': POSTGRES_DB
}


def generate_company_code(company_name: str, inn: str = None) -> str:
    """
    Генерация кода компании по рекомендации из FINAL_DECISION.md
    Приоритет: ИНН, если нет - транслитерация
    """
    if inn:
        return f"INN_{inn}"
    
    # Транслитерация
    clean_name = company_name.upper()
    clean_name = clean_name.replace('ООО', '').replace('ЗАО', '').replace('ОАО', '')
    clean_name = clean_name.replace('"', '').replace("'", '').strip()
    code = unidecode.unidecode(clean_name).replace(' ', '_')[:50]
    return code


def parse_period(period_str: str) -> str:
    """
    Конвертация периода из DuckDB формата в DATE
    '9_months_2025' → '2025-09-30'
    """
    # Используем функцию PostgreSQL parse_period
    # Здесь упрощенная версия для Python
    match = re.match(r'(\d+)_months_(\d{4})', period_str)
    if match:
        month = int(match.group(1))
        year = int(match.group(2))
        # Последний день месяца
        if month == 12:
            return f"{year}-12-31"
        else:
            from datetime import date
            d = date(year, month + 1, 1)
            d = d.replace(day=1)
            d = d.replace(day=d.day - 1) if d.day > 1 else d
            # Упрощенно: берем последний день месяца
            last_days = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
            if year % 4 == 0 and (year % 100 != 0 or year % 400 == 0):
                last_days[1] = 29
            return f"{year}-{month:02d}-{last_days[month-1]}"
    
    return period_str


class DuckDBToPostgresETL:
    def __init__(self):
        self.ddb = duckdb.connect(str(DUCKDB_PATH), read_only=True)
        self.pg_conn = psycopg2.connect(**POSTGRES_CONFIG)
        self.pg_conn.autocommit = False
        
    def __del__(self):
        if hasattr(self, 'ddb'):
            self.ddb.close()
        if hasattr(self, 'pg_conn'):
            self.pg_conn.close()
    
    def log_upload(self, company_id, period_date, source_table, filename, 
                   records_count, status, error_message=None, duration=0):
        """Запись в audit.upload_log"""
        cursor = self.pg_conn.cursor()
        cursor.execute("""
            INSERT INTO audit.upload_log 
            (company_id, period_date, source_table, source_filename, 
             records_count, status, error_message, duration_sec)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """, (company_id, period_date, source_table, filename, 
              records_count, status, error_message, duration))
    
    def migrate_master_companies(self):
        """Этап 1: Миграция справочника компаний"""
        print("=" * 80)
        print("ЭТАП 1: Миграция master.companies")
        print("=" * 80)
        
        cursor = self.pg_conn.cursor()
        
        # Компании из group_companies
        companies = self.ddb.execute("""
            SELECT DISTINCT company_name FROM group_companies
        """).fetchall()
        
        # Добавляем уникальные company_raw из osv_general (если отличаются)
        raw_companies = self.ddb.execute("""
            SELECT DISTINCT company_raw FROM osv_general
        """).fetchall()
        
        all_companies = set([c[0] for c in companies] + [c[0] for c in raw_companies])
        
        print(f"Найдено {len(all_companies)} уникальных компаний")
        
        for company_name in all_companies:
            code = generate_company_code(company_name)
            cursor.execute("""
                INSERT INTO master.companies (company_code, company_name)
                VALUES (%s, %s)
                ON CONFLICT (company_code) DO NOTHING
            """, (code, company_name))
        
        self.pg_conn.commit()
        print(f"✓ Загружено компаний: {len(all_companies)}")
    
    def migrate_master_accounts(self):
        """Этап 2: Миграция плана счетов"""
        print("\n" + "=" * 80)
        print("ЭТАП 2: Миграция master.chart_of_accounts")
        print("=" * 80)
        
        cursor = self.pg_conn.cursor()
        
        # Уникальные счета из osv_general
        accounts = self.ddb.execute("""
            SELECT DISTINCT account FROM osv_general ORDER BY account
        """).fetchall()
        
        print(f"Найдено {len(accounts)} уникальных счетов")
        
        # Базовые счета уже добавлены в схеме, остальные - заглушки
        for account, in accounts:
            account_str = str(account)
            # Определяем тип счета (упрощенно)
            account_type = 'ASSET'
            if account_str.startswith('60') or account_str.startswith('62'):
                account_type = 'ASSET'  # Расчеты
            elif account_str.startswith('90') or account_str.startswith('91'):
                account_type = 'INCOME'
            
            cursor.execute("""
                INSERT INTO master.chart_of_accounts (account_code, account_name, account_type)
                VALUES (%s, %s, %s)
                ON CONFLICT (account_code) DO NOTHING
            """, (account_str, f'Account {account_str}', account_type))
        
        self.pg_conn.commit()
        print(f"✓ Загружено счетов: {len(accounts)}")
    
    def migrate_master_counterparties(self):
        """Этап 3: Миграция контрагентов"""
        print("\n" + "=" * 80)
        print("ЭТАП 3: Миграция master.counterparties")
        print("=" * 80)
        
        cursor = self.pg_conn.cursor()
        
        # Контрагенты из osv_60
        cp_60 = self.ddb.execute("""
            SELECT DISTINCT counterparty FROM osv_60
            WHERE counterparty IS NOT NULL
        """).fetchall()
        
        # Контрагенты из osv_62
        cp_62 = self.ddb.execute("""
            SELECT DISTINCT counterparty FROM osv_62
            WHERE counterparty IS NOT NULL
        """).fetchall()
        
        all_counterparties = set([c[0] for c in cp_60] + [c[0] for c in cp_62])
        
        print(f"Найдено {len(all_counterparties)} уникальных контрагентов")
        
        for cp_name in all_counterparties:
            code = generate_company_code(cp_name)
            cursor.execute("""
                INSERT INTO master.counterparties (counterparty_code, counterparty_name)
                VALUES (%s, %s)
                ON CONFLICT (counterparty_code) DO NOTHING
            """, (code, cp_name))
        
        self.pg_conn.commit()
        print(f"✓ Загружено контрагентов: {len(all_counterparties)}")
    
    def migrate_master_dds_items(self):
        """Этап 4: Миграция статей ДДС"""
        print("\n" + "=" * 80)
        print("ЭТАП 4: Миграция master.dds_items")
        print("=" * 80)
        
        cursor = self.pg_conn.cursor()
        
        items = self.ddb.execute("""
            SELECT DISTINCT dds_item FROM osv_51
            WHERE dds_item IS NOT NULL
        """).fetchall()
        
        print(f"Найдено {len(items)} статей ДДС")
        
        for item_name, in items:
            code = generate_company_code(item_name)[:100]
            cursor.execute("""
                INSERT INTO master.dds_items (dds_item_code, dds_item_name)
                VALUES (%s, %s)
                ON CONFLICT (dds_item_code) DO NOTHING
            """, (code, item_name))
        
        self.pg_conn.commit()
        print(f"✓ Загружено статей ДДС: {len(items)}")
    
    def migrate_master_cost_items(self):
        """Этап 5: Миграция статей затрат"""
        print("\n" + "=" * 80)
        print("ЭТАП 5: Миграция master.cost_items")
        print("=" * 80)
        
        cursor = self.pg_conn.cursor()
        
        items = self.ddb.execute("""
            SELECT DISTINCT cost_item FROM osv_costs
            WHERE cost_item IS NOT NULL
        """).fetchall()
        
        print(f"Найдено {len(items)} статей затрат")
        
        for item_name, in items:
            code = generate_company_code(item_name)[:100]
            cursor.execute("""
                INSERT INTO master.cost_items (cost_item_code, cost_item_name)
                VALUES (%s, %s)
                ON CONFLICT (cost_item_code) DO NOTHING
            """, (code, item_name))
        
        self.pg_conn.commit()
        print(f"✓ Загружено статей затрат: {len(items)}")
    
    def migrate_master_periods(self):
        """Этап 6: Миграция периодов"""
        print("\n" + "=" * 80)
        print("ЭТАП 6: Миграция master.periods")
        print("=" * 80)
        
        cursor = self.pg_conn.cursor()
        
        # Уникальные периоды из всех таблиц
        periods = self.ddb.execute("""
            SELECT DISTINCT period FROM osv_general
            UNION
            SELECT DISTINCT period FROM osv_60
            UNION
            SELECT DISTINCT period FROM osv_62
            UNION
            SELECT DISTINCT period FROM osv_51
        """).fetchall()
        
        print(f"Найдено {len(periods)} уникальных периодов")
        
        for period_str, in periods:
            period_date = parse_period(period_str)
            year = int(period_date.split('-')[0])
            month = int(period_date.split('-')[1])
            quarter = (month - 1) // 3 + 1
            
            cursor.execute("""
                INSERT INTO master.periods (period_date, period_name, period_code, year, month, quarter)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (period_date) DO NOTHING
            """, (period_date, period_str, period_str, year, month, quarter))
        
        self.pg_conn.commit()
        print(f"✓ Загружено периодов: {len(periods)}")
    
    def migrate_history_osv_general(self):
        """Этап 7: Миграция osv_general → osv_detail (level 0)"""
        print("\n" + "=" * 80)
        print("ЭТАП 7: Миграция history.osv_detail (osv_general, level=0)")
        print("=" * 80)
        
        start_time = datetime.now()
        cursor = self.pg_conn.cursor()
        
        data = self.ddb.execute("""
            SELECT 
                company_raw,
                period,
                account,
                start_dt,
                start_kt,
                turn_dt,
                turn_kt,
                end_dt,
                end_kt,
                filename
            FROM osv_general
        """).fetchall()
        
        print(f"Обработка {len(data)} записей...")
        
        records = []
        for row in data:
            company_raw, period, account, start_dt, start_kt, turn_dt, turn_kt, end_dt, end_kt, filename = row
            
            # Получаем company_id
            company_code = generate_company_code(company_raw)
            cursor.execute("SELECT id FROM master.companies WHERE company_code = %s", (company_code,))
            result = cursor.fetchone()
            if not result:
                print(f"⚠ Компания не найдена: {company_raw}")
                continue
            company_id = result[0]
            
            period_date = parse_period(period)
            
            records.append((
                company_id, period_date, str(account),
                None, None, None, None,  # analytic fields
                start_dt or 0, start_kt or 0,
                turn_dt or 0, turn_kt or 0,
                end_dt or 0, end_kt or 0,
                0, 'osv_general', filename
            ))
        
        # Batch insert
        execute_batch(cursor, """
            INSERT INTO history.osv_detail (
                company_id, period_date, account_code,
                analytic_1_type, analytic_1_code, analytic_2_type, analytic_2_code,
                debit_begin, credit_begin, debit_turnover, credit_turnover, 
                debit_end, credit_end, detail_level, source_table, source_filename
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT DO NOTHING
        """, records, page_size=1000)
        
        self.pg_conn.commit()
        duration = (datetime.now() - start_time).total_seconds()
        
        self.log_upload(None, None, 'osv_general', None, len(records), 'SUCCESS', duration=duration)
        self.pg_conn.commit()
        
        print(f"✓ Загружено записей: {len(records)} (за {duration:.2f}с)")
    
    def migrate_history_osv_60(self):
        """Этап 8: Миграция osv_60 → osv_detail (level 1)"""
        print("\n" + "=" * 80)
        print("ЭТАП 8: Миграция history.osv_detail (osv_60, level=1)")
        print("=" * 80)
        
        start_time = datetime.now()
        cursor = self.pg_conn.cursor()
        
        data = self.ddb.execute("""
            SELECT 
                company_raw,
                period,
                subaccount,
                counterparty,
                initial_balance_dt,
                initial_balance_kt,
                turnover_dt,
                turnover_kt,
                final_balance_dt,
                final_balance_kt,
                filename
            FROM osv_60
        """).fetchall()
        
        print(f"Обработка {len(data)} записей...")
        
        records = []
        for row in data:
            (company_raw, period, subaccount, counterparty, 
             init_dt, init_kt, turn_dt, turn_kt, final_dt, final_kt, filename) = row
            
            # Получаем company_id
            company_code = generate_company_code(company_raw)
            cursor.execute("SELECT id FROM master.companies WHERE company_code = %s", (company_code,))
            result = cursor.fetchone()
            if not result:
                continue
            company_id = result[0]
            
            # Получаем counterparty_code
            cp_code = None
            if counterparty:
                cp_code = generate_company_code(counterparty)
            
            period_date = parse_period(period)
            
            records.append((
                company_id, period_date, str(subaccount),
                'COUNTERPARTY', cp_code, None, None,
                init_dt or 0, init_kt or 0,
                turn_dt or 0, turn_kt or 0,
                final_dt or 0, final_kt or 0,
                1, 'osv_60', filename
            ))
        
        execute_batch(cursor, """
            INSERT INTO history.osv_detail (
                company_id, period_date, account_code,
                analytic_1_type, analytic_1_code, analytic_2_type, analytic_2_code,
                debit_begin, credit_begin, debit_turnover, credit_turnover, 
                debit_end, credit_end, detail_level, source_table, source_filename
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT DO NOTHING
        """, records, page_size=1000)
        
        self.pg_conn.commit()
        duration = (datetime.now() - start_time).total_seconds()
        
        self.log_upload(None, None, 'osv_60', None, len(records), 'SUCCESS', duration=duration)
        self.pg_conn.commit()
        
        print(f"✓ Загружено записей: {len(records)} (за {duration:.2f}с)")
    
    def migrate_history_osv_62(self):
        """Этап 9: Миграция osv_62 → osv_detail (level 1)"""
        print("\n" + "=" * 80)
        print("ЭТАП 9: Миграция history.osv_detail (osv_62, level=1)")
        print("=" * 80)
        
        start_time = datetime.now()
        cursor = self.pg_conn.cursor()
        
        data = self.ddb.execute("""
            SELECT 
                company_raw,
                period,
                subaccount,
                counterparty,
                initial_balance_dt,
                initial_balance_kt,
                turnover_dt,
                turnover_kt,
                final_balance_dt,
                final_balance_kt,
                filename
            FROM osv_62
        """).fetchall()
        
        print(f"Обработка {len(data)} записей...")
        
        records = []
        for row in data:
            (company_raw, period, subaccount, counterparty, 
             init_dt, init_kt, turn_dt, turn_kt, final_dt, final_kt, filename) = row
            
            # Получаем company_id
            company_code = generate_company_code(company_raw)
            cursor.execute("SELECT id FROM master.companies WHERE company_code = %s", (company_code,))
            result = cursor.fetchone()
            if not result:
                continue
            company_id = result[0]
            
            # Получаем counterparty_code
            cp_code = None
            if counterparty:
                cp_code = generate_company_code(counterparty)
            
            period_date = parse_period(period)
            
            records.append((
                company_id, period_date, str(subaccount),
                'COUNTERPARTY', cp_code, None, None,
                init_dt or 0, init_kt or 0,
                turn_dt or 0, turn_kt or 0,
                final_dt or 0, final_kt or 0,
                1, 'osv_62', filename
            ))
        
        execute_batch(cursor, """
            INSERT INTO history.osv_detail (
                company_id, period_date, account_code,
                analytic_1_type, analytic_1_code, analytic_2_type, analytic_2_code,
                debit_begin, credit_begin, debit_turnover, credit_turnover, 
                debit_end, credit_end, detail_level, source_table, source_filename
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT DO NOTHING
        """, records, page_size=1000)
        
        self.pg_conn.commit()
        duration = (datetime.now() - start_time).total_seconds()
        
        self.log_upload(None, None, 'osv_62', None, len(records), 'SUCCESS', duration=duration)
        self.pg_conn.commit()
        
        print(f"✓ Загружено записей: {len(records)} (за {duration:.2f}с)")
    
    def migrate_history_cashflow(self):
        """Этап 10: Миграция osv_51 → cashflow_movements"""
        print("\n" + "=" * 80)
        print("ЭТАП 10: Миграция history.cashflow_movements (osv_51)")
        print("=" * 80)
        
        start_time = datetime.now()
        cursor = self.pg_conn.cursor()
        
        data = self.ddb.execute("""
            SELECT 
                company_raw,
                period,
                dds_item,
                inflow,
                outflow,
                internal_move_dt,
                internal_move_kt,
                filename
            FROM osv_51
        """).fetchall()
        
        print(f"Обработка {len(data)} записей...")
        
        records = []
        for row in data:
            company_raw, period, dds_item, inflow, outflow, int_dt, int_kt, filename = row
            
            # Получаем company_id
            company_code = generate_company_code(company_raw)
            cursor.execute("SELECT id FROM master.companies WHERE company_code = %s", (company_code,))
            result = cursor.fetchone()
            if not result:
                continue
            company_id = result[0]
            
            # Получаем dds_item_code
            dds_code = None
            if dds_item:
                dds_code = generate_company_code(dds_item)[:100]
            
            period_date = parse_period(period)
            
            records.append((
                company_id, period_date, dds_code,
                inflow or 0, outflow or 0, int_dt or 0, int_kt or 0,
                filename
            ))
        
        execute_batch(cursor, """
            INSERT INTO history.cashflow_movements (
                company_id, period_date, dds_item_code,
                inflow, outflow, internal_move_dt, internal_move_kt,
                source_filename
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT DO NOTHING
        """, records, page_size=1000)
        
        self.pg_conn.commit()
        duration = (datetime.now() - start_time).total_seconds()
        
        self.log_upload(None, None, 'osv_51', None, len(records), 'SUCCESS', duration=duration)
        self.pg_conn.commit()
        
        print(f"✓ Загружено записей: {len(records)} (за {duration:.2f}с)")
    
    def refresh_analytics(self):
        """Этап 11: Обновление аналитических представлений"""
        print("\n" + "=" * 80)
        print("ЭТАП 11: Обновление аналитики")
        print("=" * 80)
        
        cursor = self.pg_conn.cursor()
        
        try:
            cursor.execute("SELECT refresh_all_analytics()")
            result = cursor.fetchone()
            self.pg_conn.commit()
            print(f"✓ {result[0]}")
        except Exception as e:
            print(f"⚠ Ошибка обновления аналитики: {e}")
            self.pg_conn.rollback()
    
    def run_full_migration(self):
        """Полная миграция всех данных"""
        print("\n" + "=" * 80)
        print("НАЧАЛО ПОЛНОЙ МИГРАЦИИ DuckDB → PostgreSQL")
        print("=" * 80)
        print(f"Источник: {DUCKDB_PATH}")
        print(f"Назначение: {POSTGRES_CONFIG['host']}:{POSTGRES_CONFIG.get('port', 5432)}/{POSTGRES_CONFIG['dbname']}")
        print("=" * 80)
        
        try:
            # СПРАВОЧНИКИ
            self.migrate_master_companies()
            self.migrate_master_accounts()
            self.migrate_master_counterparties()
            self.migrate_master_dds_items()
            self.migrate_master_cost_items()
            self.migrate_master_periods()
            
            # ИСТОРИЯ
            self.migrate_history_osv_general()
            self.migrate_history_osv_60()
            self.migrate_history_osv_62()
            self.migrate_history_cashflow()
            
            # АНАЛИТИКА
            self.refresh_analytics()
            
            print("\n" + "=" * 80)
            print("✅ МИГРАЦИЯ ЗАВЕРШЕНА УСПЕШНО!")
            print("=" * 80)
            
        except Exception as e:
            print(f"\n❌ ОШИБКА МИГРАЦИИ: {e}")
            import traceback
            traceback.print_exc()
            self.pg_conn.rollback()
            raise


def main():
    etl = DuckDBToPostgresETL()
    etl.run_full_migration()


if __name__ == "__main__":
    main()
