#!/usr/bin/env python3
"""
ETL скрипт для загрузки данных из DuckDB в PostgreSQL.

Архитектура:
    DuckDB (osv_source.duckdb) → PostgreSQL (analytics)
    
    DuckDB schemas:
        - raw: детализация по счетам (osv_51, osv_60, etc.)
        - consolidated: агрегированные данные (osv_detailed, osv_summary)
    
    PostgreSQL schemas:
        - history: сырые OSV данные
        - analytics: агрегаты + AI результаты
        - dds: справочники и мастер-данные

Usage:
    python3 duckdb_to_postgres.py
    python3 duckdb_to_postgres.py --full  # полная перезагрузка
    python3 duckdb_to_postgres.py --incremental  # только новые записи
"""

import duckdb
import psycopg2
from psycopg2.extras import execute_batch
import os
from datetime import datetime
import argparse
import logging

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Конфигурация
DUCKDB_PATH = '/opt/docagent/data/duckdb/osv_source.duckdb'
PG_CONFIG = {
    'host': 'localhost',
    'port': 5432,
    'database': 'analytics',
    'user': 'analytics_user',
    'password': 'analytics_secure_2025'
}

class DuckDBToPostgres:
    """ETL процесс DuckDB → PostgreSQL"""
    
    def __init__(self, duck_path: str, pg_config: dict):
        self.duck_path = duck_path
        self.pg_config = pg_config
        self.duck_con = None
        self.pg_con = None
        
    def connect(self):
        """Подключение к обеим базам"""
        logger.info("Подключение к DuckDB...")
        self.duck_con = duckdb.connect(self.duck_path, read_only=True)
        
        logger.info("Подключение к PostgreSQL...")
        self.pg_con = psycopg2.connect(**self.pg_config)
        self.pg_con.autocommit = False
        
    def close(self):
        """Закрытие соединений"""
        if self.duck_con:
            self.duck_con.close()
        if self.pg_con:
            self.pg_con.close()
            
    def create_postgres_schemas(self):
        """Создание схем в PostgreSQL"""
        logger.info("Создание схем PostgreSQL...")
        
        with self.pg_con.cursor() as cur:
            # Создаем схемы
            cur.execute("CREATE SCHEMA IF NOT EXISTS history")
            cur.execute("CREATE SCHEMA IF NOT EXISTS analytics") 
            
            # Комментарии для документации
            cur.execute("""
                COMMENT ON SCHEMA history IS 
                'Сырые данные OSV из DuckDB (детализация по счетам)'
            """)
            cur.execute("""
                COMMENT ON SCHEMA analytics IS 
                'Агрегированные данные + результаты AI агентов'
            """)
            
        self.pg_con.commit()
        logger.info("✅ Схемы созданы")
        
    def load_consolidated_data(self):
        """Загрузка сырых данных OSV (DuckDB consolidated → PG history)"""
        logger.info("\n📦 Загрузка consolidated.osv_detailed в history...")
        
        # Создаем таблицу в PostgreSQL
        with self.pg_con.cursor() as cur:
            cur.execute("""
                DROP TABLE IF EXISTS history.osv_detailed CASCADE;
                CREATE TABLE history.osv_detailed (
                    id SERIAL PRIMARY KEY,
                    company_name VARCHAR(255),
                    inn VARCHAR(20),
                    period VARCHAR(20),
                    account VARCHAR(10),
                    subkonto TEXT,
                    opening_debit NUMERIC(18,2),
                    opening_credit NUMERIC(18,2),
                    turnover_debit NUMERIC(18,2),
                    turnover_credit NUMERIC(18,2),
                    closing_debit NUMERIC(18,2),
                    closing_credit NUMERIC(18,2),
                    source_file VARCHAR(255),
                    import_date TIMESTAMP,
                    etl_loaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
        self.pg_con.commit()
        
        # Загружаем данные из DuckDB
        df = self.duck_con.execute("""
            SELECT 
                company_name, inn, period, account, subkonto,
                opening_debit, opening_credit, 
                turnover_debit, turnover_credit,
                closing_debit, closing_credit,
                source_file, import_date
            FROM consolidated.osv_detailed
        """).fetchdf()
        
        logger.info(f"  Найдено {len(df)} записей в DuckDB")
        
        # Конвертируем datetime64 в string для PostgreSQL
        if 'import_date' in df.columns:
            df['import_date'] = df['import_date'].astype(str)
        
        # Заменяем NaN на None для PostgreSQL NULL
        df = df.where(df.notna(), None)
        
        # Вставка данными батчами
        if len(df) > 0:
            with self.pg_con.cursor() as cur:
                records = [tuple(row) for row in df.values]
                execute_batch(cur, """
                    INSERT INTO history.osv_detailed (
                        company_name, inn, period, account, subkonto,
                        opening_debit, opening_credit, 
                        turnover_debit, turnover_credit,
                        closing_debit, closing_credit,
                        source_file, import_date
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, list(records))
                
            self.pg_con.commit()
            logger.info(f"✅ Загружено {len(df)} записей в history.osv_detailed")
            
        # Аналогично для osv_h1_summary (H1 = first half-year data)
        logger.info("\n📦 Загрузка consolidated.osv_summary в history.osv_h1_summary...")
        
        with self.pg_con.cursor() as cur:
            cur.execute("""
                DROP TABLE IF EXISTS history.osv_h1_summary CASCADE;
                CREATE TABLE history.osv_h1_summary (
                    id SERIAL PRIMARY KEY,
                    company_name VARCHAR(255),
                    inn VARCHAR(20),
                    period VARCHAR(20),
                    account VARCHAR(10),
                    account_name TEXT,
                    opening_debit NUMERIC(18,2),
                    opening_credit NUMERIC(18,2),
                    turnover_debit NUMERIC(18,2),
                    turnover_credit NUMERIC(18,2),
                    closing_debit NUMERIC(18,2),
                    closing_credit NUMERIC(18,2),
                    source_file VARCHAR(255),
                    import_date TIMESTAMP,
                    etl_loaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
        df_summary = self.duck_con.execute("""
            SELECT 
                company_name, inn, period, account, account_name,
                opening_debit, opening_credit, 
                turnover_debit, turnover_credit,
                closing_debit, closing_credit,
                source_file, import_date
            FROM consolidated.osv_summary
        """).fetchdf()
        
        logger.info(f"  Найдено {len(df_summary)} записей в DuckDB")
        
        # Конвертируем datetime64 в string
        if 'import_date' in df_summary.columns:
            df_summary['import_date'] = df_summary['import_date'].astype(str)
        
        # Заменяем NaN на None
        df_summary = df_summary.where(df_summary.notna(), None)
        
        if len(df_summary) > 0:
            with self.pg_con.cursor() as cur:
                records = [tuple(row) for row in df_summary.values]
                execute_batch(cur, """
                    INSERT INTO history.osv_h1_summary (
                        company_name, inn, period, account, account_name,
                        opening_debit, opening_credit, 
                        turnover_debit, turnover_credit,
                        closing_debit, closing_credit,
                        source_file, import_date
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, list(records))
                
            self.pg_con.commit()
            logger.info(f"✅ Загружено {len(df_summary)} записей в history.osv_h1_summary")
            
    def load_raw_data(self):
        """Загрузка детализированных данных (DuckDB raw → PG history)"""
        logger.info("\n📦 Загрузка raw.osv_51 (расчетные счета)...")
        
        with self.pg_con.cursor() as cur:
            cur.execute("""
                DROP TABLE IF EXISTS history.osv_51 CASCADE;
                CREATE TABLE history.osv_51 (
                    id SERIAL PRIMARY KEY,
                    filename VARCHAR(255),
                    company_raw VARCHAR(255),
                    period VARCHAR(20),
                    dds_item TEXT,
                    inflow NUMERIC(18,2),
                    outflow NUMERIC(18,2),
                    internal_move_dt NUMERIC(18,2),
                    internal_move_kt BIGINT,
                    etl_loaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
        df = self.duck_con.execute("SELECT * FROM raw.osv_51").fetchdf()
        logger.info(f"  Найдено {len(df)} записей")
        
        if len(df) > 0:
            with self.pg_con.cursor() as cur:
                records = [tuple(row) for row in df.values]
                execute_batch(cur, """
                    INSERT INTO history.osv_51 (
                        filename, company_raw, period, dds_item, 
                        inflow, outflow, internal_move_dt, internal_move_kt
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """, list(records))
                
            self.pg_con.commit()
            logger.info(f"✅ Загружено {len(df)} записей в history.osv_51")
            
        # Аналогично для остальных счетов (60, 62, 91)
        for account in ['60', '62', '91']:
            logger.info(f"\n📦 Загрузка raw.osv_{account}...")
            
            # Получаем структуру таблицы из DuckDB
            df_account = self.duck_con.execute(f"SELECT * FROM raw.osv_{account} LIMIT 1").fetchdf()
            
            if len(df_account.columns) > 0:
                # Создаем таблицу динамически на основе DuckDB схемы
                columns_def = []
                for col in df_account.columns:
                    dtype = df_account[col].dtype
                    if dtype == 'object':
                        pg_type = 'TEXT'
                    elif dtype == 'float64':
                        pg_type = 'NUMERIC(18,2)'
                    elif dtype == 'int64':
                        pg_type = 'BIGINT'
                    else:
                        pg_type = 'TEXT'
                    columns_def.append(f"{col} {pg_type}")
                
                with self.pg_con.cursor() as cur:
                    cur.execute(f"""
                        DROP TABLE IF EXISTS history.osv_{account} CASCADE;
                        CREATE TABLE history.osv_{account} (
                            id SERIAL PRIMARY KEY,
                            {', '.join(columns_def)},
                            etl_loaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                        )
                    """)
                    
                df_full = self.duck_con.execute(f"SELECT * FROM raw.osv_{account}").fetchdf()
                logger.info(f"  Найдено {len(df_full)} записей")
                
                # Обработка NaN и datetime
                df_full = df_full.where(df_full.notna(), None)
                for col in df_full.columns:
                    if df_full[col].dtype == 'datetime64[ns]':
                        df_full[col] = df_full[col].astype(str)
                
                if len(df_full) > 0:
                    records = [tuple(row) for row in df_full.values]
                    placeholders = ', '.join(['%s'] * len(df_full.columns))
                    col_names = ', '.join(df_full.columns)
                    
                    with self.pg_con.cursor() as cur:
                        execute_batch(cur, f"""
                            INSERT INTO history.osv_{account} ({col_names})
                            VALUES ({placeholders})
                        """, list(records))
                        
                    self.pg_con.commit()
                    logger.info(f"✅ Загружено {len(df_full)} записей в history.osv_{account}")
                    
    def load_costs_data(self):
        """Загрузка данных затрат по счетам 20, 26, 44 (DuckDB raw → PG history)"""
        logger.info("\n📦 Загрузка raw.osv_costs → history.osv_9m_costs (структура затрат за 9 месяцев)...")
        
        with self.pg_con.cursor() as cur:
            cur.execute("""
                DROP TABLE IF EXISTS history.osv_9m_costs CASCADE;
                CREATE TABLE history.osv_9m_costs (
                    id SERIAL PRIMARY KEY,
                    filename VARCHAR(255),
                    company_raw VARCHAR(255),
                    period VARCHAR(50),
                    account_type VARCHAR(10),
                    cost_item TEXT,
                    amount_dt NUMERIC(18,2),
                    amount_kt NUMERIC(18,2),
                    etl_loaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
        df = self.duck_con.execute("SELECT * FROM raw.osv_costs").fetchdf()
        logger.info(f"  Найдено {len(df)} записей")
        
        if len(df) > 0:
            # Заменяем NaN на None
            df = df.where(df.notna(), None)
            
            with self.pg_con.cursor() as cur:
                records = [tuple(row) for row in df.values]
                execute_batch(cur, """
                    INSERT INTO history.osv_9m_costs (
                        filename, company_raw, period, account_type, 
                        cost_item, amount_dt, amount_kt
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                """, list(records))
                
            self.pg_con.commit()
            logger.info(f"✅ Загружено {len(df)} записей в history.osv_9m_costs")
            
            # Статистика по счетам
            stats = self.duck_con.execute("""
                SELECT account_type, COUNT(*) as cnt 
                FROM raw.osv_costs 
                GROUP BY account_type 
                ORDER BY account_type
            """).fetchdf()
            for _, row in stats.iterrows():
                logger.info(f"  Счет {row['account_type']}: {row['cnt']} записей")
    
    def load_reference_data(self):
        """Загрузка справочников (DuckDB raw → уже есть в master схеме PostgreSQL)"""
        logger.info("\n📦 Справочники уже существуют в схеме master")
        logger.info("  Пропускаем загрузку - используем существующие данные")
        # Справочники companies уже в master.companies
        # Дополнительную загрузку не требуется
            
    def create_analytics_views(self):
        """Создание аналитических представлений"""
        logger.info("\n📊 Создание аналитических представлений...")
        
        with self.pg_con.cursor() as cur:
            # View: Консолидация по организациям (из history.osv_detailed)
            cur.execute("""
                CREATE OR REPLACE VIEW analytics.v_consolidated_by_org AS
                SELECT 
                    company_name,
                    inn,
                    period,
                    SUM(turnover_debit) as total_debit,
                    SUM(turnover_credit) as total_credit,
                    SUM(closing_debit - opening_debit) as debit_change,
                    SUM(closing_credit - opening_credit) as credit_change
                FROM history.osv_detailed
                GROUP BY company_name, inn, period
                ORDER BY company_name, period
            """)
            
            # View: Сводка затрат по компаниям (из history.osv_9m_costs)
            cur.execute("""
                CREATE OR REPLACE VIEW analytics.v_costs_by_company AS
                SELECT 
                    company_raw as company_name,
                    account_type,
                    period,
                    COUNT(DISTINCT cost_item) as items_count,
                    SUM(amount_dt) as total_costs_dt,
                    SUM(amount_kt) as total_costs_kt,
                    SUM(amount_dt - amount_kt) as net_costs
                FROM history.osv_9m_costs
                GROUP BY company_raw, account_type, period
                ORDER BY company_raw, account_type
            """)
            
        self.pg_con.commit()
        logger.info("✅ Представления созданы")
        
    def run_full_etl(self):
        """Полный ETL процесс"""
        try:
            self.connect()
            
            logger.info("="*60)
            logger.info("СТАРТ ETL: DuckDB → PostgreSQL")
            logger.info("="*60)
            
            self.create_postgres_schemas()
            self.load_reference_data()
            self.load_consolidated_data()
            self.load_raw_data()
            self.load_costs_data()
            self.create_analytics_views()
            
            logger.info("\n" + "="*60)
            logger.info("✅ ETL ЗАВЕРШЕН УСПЕШНО")
            logger.info("="*60)
            
            # Статистика
            with self.pg_con.cursor() as cur:
                cur.execute("""
                    SELECT 
                        schemaname, 
                        relname as tablename, 
                        n_live_tup as row_count
                    FROM pg_stat_user_tables
                    WHERE schemaname IN ('history', 'analytics', 'master')
                    ORDER BY schemaname, relname
                """)
                
                logger.info("\n📊 Статистика загруженных данных:")
                for row in cur.fetchall():
                    logger.info(f"  {row[0]}.{row[1]}: {row[2]:,} записей")
                    
        except Exception as e:
            logger.error(f"❌ Ошибка ETL: {e}")
            if self.pg_con:
                self.pg_con.rollback()
            raise
        finally:
            self.close()


def main():
    parser = argparse.ArgumentParser(description='ETL: DuckDB → PostgreSQL')
    parser.add_argument('--full', action='store_true', help='Полная перезагрузка')
    parser.add_argument('--incremental', action='store_true', help='Инкрементальная загрузка')
    args = parser.parse_args()
    
    etl = DuckDBToPostgres(DUCKDB_PATH, PG_CONFIG)
    
    if args.incremental:
        logger.info("Режим: инкрементальная загрузка (TODO)")
        # TODO: реализовать инкрементальную загрузку
    else:
        etl.run_full_etl()


if __name__ == '__main__':
    main()
