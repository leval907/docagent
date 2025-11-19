import pandas as pd
import duckdb
from typing import Tuple, Dict, Any
from finance_core.db.connector import DBManager

class RevenueConsolidator:
    """
    Класс для консолидации выручки и анализа данных из DuckDB.
    """
    
    def __init__(self):
        self.db_manager = DBManager()

    def analyze_revenue_structure(self) -> Dict[str, Any]:
        """
        Анализирует структуру выручки по типам проводок.
        Возвращает словарь со статистикой.
        """
        conn = self.db_manager.get_duckdb_conn()
        stats = {}
        
        try:
            # Получаем список колонок
            columns = [row[0] for row in conn.execute("DESCRIBE revenue_raw").fetchall()]
            
            # Определяем запросы для разных типов проводок
            queries = {
                "62_90": "Дт62 Кт90 (основная деятельность)",
                "62_91": "Дт62 Кт91 (прочие доходы)",
                "51_62": "Дт51 Кт62 (оплата от покупателей)",
                "60_62": "Д60 К62 (взаимозачет)",
                "62_51": "Дт62 Кт51 (возврат аванса)",
                "76_62": "Дт76 Кт62 (расчёты с разными дебиторами)"
            }
            
            for col, desc in queries.items():
                if col in columns:
                    query = f"""
                    SELECT 
                        SUM(COALESCE("{col}", 0)) as total,
                        COUNT(*) as doc_count
                    FROM revenue_raw
                    WHERE COALESCE("{col}", 0) > 0
                    """
                    res = conn.execute(query).fetchone()
                    stats[col] = {
                        "description": desc,
                        "total": res[0] if res[0] else 0.0,
                        "count": res[1]
                    }
                else:
                    stats[col] = {"description": desc, "total": 0.0, "count": 0}
                    
            return stats
            
        finally:
            conn.close()

    def get_consolidated_data(self) -> pd.DataFrame:
        """
        Получает консолидированные данные по компаниям.
        """
        conn = self.db_manager.get_duckdb_conn()
        try:
            # Проверяем наличие таблиц
            tables = [t[0] for t in conn.execute("SHOW TABLES").fetchall()]
            if 'revenue_raw' not in tables:
                raise ValueError("Таблица revenue_raw не найдена")
            
            group_companies = []
            if 'group_companies' in tables:
                group_companies = conn.execute("SELECT company_name FROM group_companies").fetchdf()['company_name'].tolist()
            
            # Формируем условие для внутригрупповых оборотов
            if group_companies:
                like_conditions = ' OR '.join([
                    f"UPPER(\"Контрагент\") LIKE '%{comp.upper()}%'" 
                    for comp in group_companies
                ])
            else:
                like_conditions = "FALSE"
            
            columns = [row[0] for row in conn.execute("DESCRIBE revenue_raw").fetchall()]
            
            # Helper to safely select columns
            def safe_col(col, alias):
                return f'COALESCE("{col}", 0) as {alias}' if col in columns else f'0 as {alias}'

            select_parts = [
                safe_col("Начальное сальдо Дт", "начальное_сальдо_дт"),
                safe_col("Начальное сальдо Кт", "начальное_сальдо_кт"),
                safe_col("62_90", "счет_90"),
                safe_col("62_91", "счет_91"),
                safe_col("51_62", "оплата_51"),
                safe_col("60_62", "взаимозачет_60"),
                safe_col("76_62", "оплата_76"),
                safe_col("62_51", "возврат_62_51"),
                safe_col("Конечное сальдо Дт", "конечное_сальдо_дт"),
                safe_col("Конечное сальдо Кт", "конечное_сальдо_кт")
            ]

            query = f"""
            WITH revenue_transactions AS (
                SELECT
                    "Компания",
                    "Контрагент",
                    "Документ",
                    {', '.join(select_parts)},
                    COALESCE("62_90", 0) + COALESCE("62_91", 0) as выручка_начислено,
                    CASE
                        WHEN {like_conditions} THEN TRUE
                        ELSE FALSE
                    END as внутригрупповая
                FROM revenue_raw
                WHERE (COALESCE("62_90", 0) > 0 OR COALESCE("62_91", 0) > 0)
            )
            SELECT
                "Компания",
                SUM(начальное_сальдо_дт) as начальное_сальдо_дт,
                SUM(начальное_сальдо_кт) as начальное_сальдо_кт,
                SUM(выручка_начислено) as выручка_всего,
                SUM(CASE WHEN внутригрупповая THEN выручка_начислено ELSE 0 END) as внутригрупповая_выручка,
                SUM(CASE WHEN NOT внутригрупповая THEN выручка_начислено ELSE 0 END) as внешняя_выручка,
                SUM(счет_90) as счет_90_основная,
                SUM(счет_91) as счет_91_прочие,
                SUM(оплата_51) as оплачено_51,
                SUM(взаимозачет_60) as взаимозачет_60,
                SUM(оплата_76) as оплачено_76,
                SUM(возврат_62_51) as возврат_аванса,
                SUM(конечное_сальдо_дт) as конечное_сальдо_дт,
                SUM(конечное_сальдо_кт) as конечное_сальдо_кт,
                COUNT(*) as документов
            FROM revenue_transactions
            GROUP BY "Компания"
            ORDER BY "Компания";
            """
            
            return conn.execute(query).df()
            
        finally:
            conn.close()

    def get_detailed_data(self) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        Возвращает детальные данные, разделенные на внешнюю и внутригрупповую выручку.
        Returns: (external_df, internal_df)
        """
        conn = self.db_manager.get_duckdb_conn()
        try:
            tables = [t[0] for t in conn.execute("SHOW TABLES").fetchall()]
            if 'revenue_raw' not in tables:
                return pd.DataFrame(), pd.DataFrame()

            group_companies = []
            if 'group_companies' in tables:
                group_companies = conn.execute("SELECT company_name FROM group_companies").fetchdf()['company_name'].tolist()

            if group_companies:
                like_conditions = ' OR '.join([
                    f"UPPER(\"Контрагент\") LIKE '%{comp.upper()}%'" 
                    for comp in group_companies
                ])
            else:
                like_conditions = "FALSE"

            columns = [row[0] for row in conn.execute("DESCRIBE revenue_raw").fetchall()]
            
            def safe_col(col, alias):
                return f'COALESCE("{col}", 0) as {alias}' if col in columns else f'0 as {alias}'

            select_parts = [
                safe_col("Начальное сальдо Дт", "начальное_сальдо_дт"),
                safe_col("Начальное сальдо Кт", "начальное_сальдо_кт"),
                safe_col("62_90", "счет_90_основная"),
                safe_col("62_91", "счет_91_прочие"),
                safe_col("51_62", "оплата_51"),
                safe_col("60_62", "взаимозачет_60"),
                safe_col("76_62", "оплата_76"),
                safe_col("Конечное сальдо Дт", "конечное_сальдо_дт"),
                safe_col("Конечное сальдо Кт", "конечное_сальдо_кт")
            ]

            query = f"""
            SELECT
                "Компания",
                "Контрагент",
                "Документ",
                {', '.join(select_parts)},
                COALESCE("62_90", 0) + COALESCE("62_91", 0) as выручка_начислено,
                CASE
                    WHEN {like_conditions} THEN 'Внутригрупповая'
                    ELSE 'Внешняя'
                END as тип_контрагента
            FROM revenue_raw
            WHERE (COALESCE("62_90", 0) > 0 OR COALESCE("62_91", 0) > 0)
            ORDER BY "Компания", тип_контрагента, "Контрагент", "Документ";
            """
            
            df = conn.execute(query).df()
            
            external_df = df[df['тип_контрагента'] == 'Внешняя'].drop(columns=['тип_контрагента'])
            internal_df = df[df['тип_контрагента'] == 'Внутригрупповая'].drop(columns=['тип_контрагента'])
            
            return external_df, internal_df
            
        finally:
            conn.close()
