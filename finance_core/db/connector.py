import duckdb
import psycopg2
from arango import ArangoClient
from finance_core.config import (
    DUCKDB_PATH, 
    ARANGO_HOST, ARANGO_PORT, ARANGO_USER, ARANGO_PASSWORD, ARANGO_DB_NAME,
    POSTGRES_HOST, POSTGRES_PORT, POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_DB
)

class DBManager:
    def __init__(self):
        self.duckdb_path = str(DUCKDB_PATH)
        self._arango_client = None
        self._arango_db = None

    def get_duckdb_conn(self, read_only=True):
        """Returns a connection to DuckDB."""
        return duckdb.connect(self.duckdb_path, read_only=read_only)

    def get_postgres_conn(self):
        """Returns a connection to PostgreSQL."""
        return psycopg2.connect(
            host=POSTGRES_HOST,
            port=POSTGRES_PORT,
            user=POSTGRES_USER,
            password=POSTGRES_PASSWORD,
            database=POSTGRES_DB
        )

    def get_arango_db(self):
        """Returns a connection to the ArangoDB database."""
        if self._arango_db is None:
            # Initialize client
            hosts = f"http://{ARANGO_HOST}:{ARANGO_PORT}"
            self._arango_client = ArangoClient(hosts=hosts)
            
            # Connect to system db to check/create target db
            sys_db = self._arango_client.db('_system', username=ARANGO_USER, password=ARANGO_PASSWORD)
            
            if not sys_db.has_database(ARANGO_DB_NAME):
                sys_db.create_database(ARANGO_DB_NAME)
            
            # Connect to target db
            self._arango_db = self._arango_client.db(ARANGO_DB_NAME, username=ARANGO_USER, password=ARANGO_PASSWORD)
            
        return self._arango_db

    def close(self):
        if self._arango_client:
            self._arango_client.close()
