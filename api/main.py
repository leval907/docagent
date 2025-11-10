"""
DocAgent FastAPI - REST API для доступа к документации
"""
from fastapi import FastAPI, HTTPException, Query, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import os
from datetime import datetime
import psycopg2
import chromadb
import duckdb
from loguru import logger

# Конфигурация
POSTGRES_URL = os.getenv("POSTGRES_URL")
CHROMA_URL = os.getenv("CHROMA_URL", "http://chromadb:8000")
DUCKDB_PATH = os.getenv("DUCKDB_PATH", "/app/data/analytics.duckdb")
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "*").split(",")

# Инициализация FastAPI
app = FastAPI(
    title="DocAgent API",
    description="REST API для поиска и управления документацией",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic модели
class Document(BaseModel):
    id: int
    app_id: str
    url: str
    title: Optional[str]
    s3_path: Optional[str]
    word_count: Optional[int]
    created_at: datetime

class SearchRequest(BaseModel):
    query: str
    app_id: Optional[str] = None
    limit: int = 10

class SearchResult(BaseModel):
    document_id: int
    url: str
    title: str
    chunk_text: str
    similarity: float
    metadata: Dict[str, Any]

class CrawlStats(BaseModel):
    app_id: str
    pages_crawled: int
    pages_cleaned: int
    pages_uploaded: int
    total_words: int
    duration_seconds: float
    completed_at: datetime

# Dependency: PostgreSQL connection
def get_db():
    conn = psycopg2.connect(POSTGRES_URL)
    try:
        yield conn
    finally:
        conn.close()

# Dependency: ChromaDB client
def get_chroma():
    client = chromadb.HttpClient(host=CHROMA_URL.replace("http://", "").split(":")[0])
    return client

# Dependency: DuckDB connection
def get_duckdb():
    conn = duckdb.connect(DUCKDB_PATH)
    try:
        yield conn
    finally:
        conn.close()

# ============================================
# Health Check
# ============================================

@app.get("/health")
async def health_check():
    """Проверка здоровья сервиса"""
    try:
        # Проверка PostgreSQL
        conn = psycopg2.connect(POSTGRES_URL)
        conn.close()
        pg_status = "ok"
    except Exception as e:
        pg_status = f"error: {str(e)}"
    
    try:
        # Проверка ChromaDB
        chroma = chromadb.HttpClient(host=CHROMA_URL.replace("http://", "").split(":")[0])
        chroma.heartbeat()
        chroma_status = "ok"
    except Exception as e:
        chroma_status = f"error: {str(e)}"
    
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "services": {
            "postgresql": pg_status,
            "chromadb": chroma_status,
            "duckdb": "ok"
        }
    }

# ============================================
# Documents API
# ============================================

@app.get("/documents", response_model=List[Document])
async def list_documents(
    app_id: Optional[str] = None,
    limit: int = Query(100, le=1000),
    offset: int = 0,
    conn = Depends(get_db)
):
    """Список документов"""
    cur = conn.cursor()
    
    if app_id:
        cur.execute(
            "SELECT id, app_id, url, title, s3_path, word_count, created_at "
            "FROM documents WHERE app_id = %s ORDER BY created_at DESC LIMIT %s OFFSET %s",
            (app_id, limit, offset)
        )
    else:
        cur.execute(
            "SELECT id, app_id, url, title, s3_path, word_count, created_at "
            "FROM documents ORDER BY created_at DESC LIMIT %s OFFSET %s",
            (limit, offset)
        )
    
    rows = cur.fetchall()
    cur.close()
    
    return [
        Document(
            id=row[0],
            app_id=row[1],
            url=row[2],
            title=row[3],
            s3_path=row[4],
            word_count=row[5],
            created_at=row[6]
        )
        for row in rows
    ]

@app.get("/documents/{document_id}", response_model=Document)
async def get_document(document_id: int, conn = Depends(get_db)):
    """Получить документ по ID"""
    cur = conn.cursor()
    cur.execute(
        "SELECT id, app_id, url, title, s3_path, word_count, created_at "
        "FROM documents WHERE id = %s",
        (document_id,)
    )
    row = cur.fetchone()
    cur.close()
    
    if not row:
        raise HTTPException(status_code=404, detail="Document not found")
    
    return Document(
        id=row[0],
        app_id=row[1],
        url=row[2],
        title=row[3],
        s3_path=row[4],
        word_count=row[5],
        created_at=row[6]
    )

# ============================================
# Vector Search API (ChromaDB)
# ============================================

@app.post("/search", response_model=List[SearchResult])
async def vector_search(request: SearchRequest):
    """Векторный поиск по документам"""
    try:
        chroma = get_chroma()
        collection = chroma.get_or_create_collection("documents")
        
        # Поиск
        results = collection.query(
            query_texts=[request.query],
            n_results=request.limit,
            where={"app_id": request.app_id} if request.app_id else None
        )
        
        # Форматирование результатов
        search_results = []
        for i in range(len(results['ids'][0])):
            search_results.append(SearchResult(
                document_id=int(results['metadatas'][0][i].get('document_id', 0)),
                url=results['metadatas'][0][i].get('url', ''),
                title=results['metadatas'][0][i].get('title', ''),
                chunk_text=results['documents'][0][i],
                similarity=1.0 - results['distances'][0][i],  # convert distance to similarity
                metadata=results['metadatas'][0][i]
            ))
        
        return search_results
    
    except Exception as e:
        logger.error(f"Search error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ============================================
# Statistics API (DuckDB)
# ============================================

@app.get("/stats/crawls", response_model=List[CrawlStats])
async def get_crawl_stats(
    app_id: Optional[str] = None,
    limit: int = Query(10, le=100),
    conn = Depends(get_db)
):
    """Статистика краулинга"""
    cur = conn.cursor()
    
    if app_id:
        cur.execute(
            "SELECT app_id, pages_crawled, pages_cleaned, pages_uploaded, "
            "total_words, duration_seconds, completed_at "
            "FROM crawl_stats WHERE app_id = %s "
            "ORDER BY completed_at DESC LIMIT %s",
            (app_id, limit)
        )
    else:
        cur.execute(
            "SELECT app_id, pages_crawled, pages_cleaned, pages_uploaded, "
            "total_words, duration_seconds, completed_at "
            "FROM crawl_stats ORDER BY completed_at DESC LIMIT %s",
            (limit,)
        )
    
    rows = cur.fetchall()
    cur.close()
    
    return [
        CrawlStats(
            app_id=row[0],
            pages_crawled=row[1],
            pages_cleaned=row[2],
            pages_uploaded=row[3],
            total_words=row[4],
            duration_seconds=row[5],
            completed_at=row[6]
        )
        for row in rows
    ]

@app.get("/stats/analytics")
async def get_analytics(duckdb_conn = Depends(get_duckdb)):
    """Аналитика с помощью DuckDB"""
    try:
        # Подключение к PostgreSQL через DuckDB
        duckdb_conn.execute(f"""
            ATTACH '{POSTGRES_URL}' AS pg (TYPE postgres, READ_ONLY);
        """)
        
        # Агрегированная статистика
        stats = duckdb_conn.execute("""
            SELECT 
                app_id,
                COUNT(*) as total_documents,
                SUM(word_count) as total_words,
                AVG(word_count) as avg_words_per_doc,
                MIN(created_at) as first_crawl,
                MAX(created_at) as last_crawl
            FROM pg.documents
            GROUP BY app_id
            ORDER BY total_documents DESC
        """).fetchall()
        
        return {
            "apps": [
                {
                    "app_id": row[0],
                    "total_documents": row[1],
                    "total_words": row[2],
                    "avg_words_per_doc": float(row[3]) if row[3] else 0,
                    "first_crawl": row[4].isoformat() if row[4] else None,
                    "last_crawl": row[5].isoformat() if row[5] else None
                }
                for row in stats
            ]
        }
    except Exception as e:
        logger.error(f"Analytics error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ============================================
# Apps API
# ============================================

@app.get("/apps")
async def list_apps(conn = Depends(get_db)):
    """Список приложений с документацией"""
    cur = conn.cursor()
    cur.execute("""
        SELECT 
            app_id,
            COUNT(*) as document_count,
            SUM(word_count) as total_words,
            MAX(created_at) as last_updated
        FROM documents
        GROUP BY app_id
        ORDER BY document_count DESC
    """)
    
    rows = cur.fetchall()
    cur.close()
    
    return {
        "apps": [
            {
                "app_id": row[0],
                "document_count": row[1],
                "total_words": row[2] or 0,
                "last_updated": row[3].isoformat() if row[3] else None
            }
            for row in rows
        ]
    }

# ============================================
# Root
# ============================================

@app.get("/")
async def root():
    """API информация"""
    return {
        "name": "DocAgent API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
