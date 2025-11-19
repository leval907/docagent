import os
from pathlib import Path

# Base paths
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DB_DIR = DATA_DIR / "db"

# Database paths
DUCKDB_PATH = DB_DIR / "osv_database.duckdb"

# ArangoDB settings
ARANGO_HOST = os.getenv("ARANGO_HOST", "arangodb")
ARANGO_PORT = int(os.getenv("ARANGO_PORT", 8529))
ARANGO_USER = os.getenv("ARANGO_USER", "root")
ARANGO_PASSWORD = os.getenv("ARANGO_PASSWORD", "strongpassword")
ARANGO_DB_NAME = os.getenv("ARANGO_DB_NAME", "finance_analytics")

# Input/Output paths
INPUT_FILES_DIR = DATA_DIR / "osv_revenue_0925" / "input"
OUTPUT_FILES_DIR = DATA_DIR / "osv_revenue_0925" / "output"
GROUP_COMPANIES_FILE = DATA_DIR / "group_companies.xlsx"
