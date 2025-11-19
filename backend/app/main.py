from fastapi import FastAPI, HTTPException, BackgroundTasks
from finance_core.db.connector import DBManager
from finance_core.etl.normalizer import OSVNormalizer
from finance_core.etl.importer import DuckDBImporter
from finance_core.analysis.consolidation import RevenueConsolidator
from finance_core.analysis.graph_builder import GraphBuilder
from finance_core.config import INPUT_FILES_DIR, GROUP_COMPANIES_FILE
import pandas as pd

app = FastAPI(title="Finance Analysis API")
db_manager = DBManager()

@app.get("/")
def read_root():
    return {"message": "Finance Analysis API is running"}

@app.get("/health")
def health_check():
    try:
        # Check DuckDB
        duck_conn = db_manager.get_duckdb_conn()
        duck_conn.execute("SELECT 1")
        duck_status = "ok"
        duck_conn.close()
    except Exception as e:
        duck_status = f"error: {str(e)}"

    try:
        # Check ArangoDB
        arango_db = db_manager.get_arango_db()
        arango_info = arango_db.properties()
        arango_status = "ok"
    except Exception as e:
        arango_status = f"error: {str(e)}"

    return {
        "duckdb": duck_status,
        "arangodb": arango_status
    }

# === ETL Endpoints ===

@app.post("/etl/run")
async def run_full_etl(background_tasks: BackgroundTasks):
    """
    Запускает полный цикл ETL: Нормализация -> Импорт -> Построение графа.
    Выполняется в фоне.
    """
    background_tasks.add_task(_run_etl_process)
    return {"message": "ETL process started in background"}

def _run_etl_process():
    try:
        print("🚀 Starting ETL process...")
        
        # 1. Normalize
        normalizer = OSVNormalizer(group_companies_file=GROUP_COMPANIES_FILE)
        df = normalizer.process_directory(INPUT_FILES_DIR)
        
        if df.empty:
            print("⚠️ No data found to normalize")
            return

        # 2. Import to DuckDB
        importer = DuckDBImporter()
        importer.import_revenue_data(df)
        importer.import_group_companies(normalizer.group_companies)
        
        # 3. Build Graph
        graph_builder = GraphBuilder()
        graph_builder.build_graph_from_duckdb()
        
        print("✅ ETL process completed successfully")
    except Exception as e:
        print(f"❌ ETL process failed: {e}")

# === Analytics Endpoints ===

@app.get("/revenue/summary")
def get_revenue_summary():
    """Возвращает сводную таблицу выручки по компаниям"""
    try:
        consolidator = RevenueConsolidator()
        df = consolidator.get_consolidated_data()
        # Convert NaN to None for JSON serialization
        return df.where(pd.notnull(df), None).to_dict(orient="records")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/revenue/structure")
def get_revenue_structure():
    """Возвращает структуру выручки по типам проводок"""
    try:
        consolidator = RevenueConsolidator()
        return consolidator.analyze_revenue_structure()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# === Graph Endpoints ===

@app.post("/graph/build")
def build_graph():
    """Принудительно перестраивает граф в ArangoDB"""
    try:
        graph_builder = GraphBuilder()
        graph_builder.build_graph_from_duckdb()
        return {"message": "Graph rebuilt successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/graph/stats")
def get_graph_stats():
    """Возвращает статистику графа"""
    try:
        db = db_manager.get_arango_db()
        companies_count = db.collection('Companies').count()
        transactions_count = db.collection('Transactions').count()
        return {
            "companies": companies_count,
            "transactions": transactions_count
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

