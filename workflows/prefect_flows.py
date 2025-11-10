"""
Prefect Workflows для DocAgent
Оркестрация процессов crawl → clean → embed → store
"""
from prefect import flow, task
from prefect.task_runners import ConcurrentTaskRunner
from datetime import timedelta
import sys
import os

# Добавляем путь к скриптам
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from scripts.crawl_and_clean import DocumentPipeline
import chromadb
import psycopg2
from loguru import logger

# ============================================
# Tasks
# ============================================

@task(retries=3, retry_delay_seconds=60)
def crawl_documentation(app_id: str, config: dict):
    """Краулинг документации"""
    logger.info(f"Starting crawl for {app_id}")
    
    pipeline = DocumentPipeline()
    
    # Настройка S3
    if config.get('s3_bucket'):
        pipeline.setup_s3(
            bucket=config['s3_bucket'],
            endpoint=config.get('s3_endpoint'),
            access_key=os.getenv('AWS_ACCESS_KEY_ID'),
            secret_key=os.getenv('AWS_SECRET_ACCESS_KEY')
        )
    
    # Настройка PostgreSQL
    if config.get('pg_host'):
        pipeline.setup_postgres(
            host=config['pg_host'],
            database=config['pg_database'],
            user=config['pg_user'],
            password=config['pg_password']
        )
    
    # Запуск процесса
    result = pipeline.process_app(app_id)
    
    logger.success(f"Crawl completed for {app_id}: {result['pages_crawled']} pages")
    return result

@task
def generate_embeddings(app_id: str, documents: list, chroma_url: str):
    """Генерация embeddings и загрузка в ChromaDB"""
    logger.info(f"Generating embeddings for {app_id}: {len(documents)} documents")
    
    try:
        # Подключение к ChromaDB
        chroma_client = chromadb.HttpClient(host=chroma_url.replace("http://", "").split(":")[0])
        collection = chroma_client.get_or_create_collection(
            name="documents",
            metadata={"description": "DocAgent documentation embeddings"}
        )
        
        # Подготовка данных для ChromaDB
        ids = []
        documents_texts = []
        metadatas = []
        
        for doc in documents:
            # Разбиение на чанки (каждый ~500 токенов)
            chunks = split_into_chunks(doc['content'], chunk_size=500)
            
            for i, chunk in enumerate(chunks):
                chunk_id = f"{doc['id']}_chunk_{i}"
                ids.append(chunk_id)
                documents_texts.append(chunk)
                metadatas.append({
                    'document_id': doc['id'],
                    'app_id': app_id,
                    'url': doc['url'],
                    'title': doc.get('title', ''),
                    'chunk_index': i,
                    'total_chunks': len(chunks)
                })
        
        # Добавление в ChromaDB (автоматическая генерация embeddings)
        collection.add(
            ids=ids,
            documents=documents_texts,
            metadatas=metadatas
        )
        
        logger.success(f"Added {len(ids)} chunks to ChromaDB for {app_id}")
        return {"chunks_added": len(ids)}
    
    except Exception as e:
        logger.error(f"Embedding generation failed: {e}")
        raise

@task
def update_analytics(app_id: str, crawl_stats: dict, duckdb_path: str):
    """Обновление аналитики в DuckDB"""
    logger.info(f"Updating analytics for {app_id}")
    
    import duckdb
    
    conn = duckdb.connect(duckdb_path)
    
    # Создание таблицы аналитики если не существует
    conn.execute("""
        CREATE TABLE IF NOT EXISTS crawl_analytics (
            app_id VARCHAR,
            crawl_date DATE,
            pages_crawled INTEGER,
            pages_cleaned INTEGER,
            total_words INTEGER,
            duration_seconds FLOAT,
            success_rate FLOAT,
            PRIMARY KEY (app_id, crawl_date)
        )
    """)
    
    # Вставка данных
    conn.execute("""
        INSERT OR REPLACE INTO crawl_analytics 
        VALUES (?, CURRENT_DATE, ?, ?, ?, ?, ?)
    """, (
        app_id,
        crawl_stats['pages_crawled'],
        crawl_stats['pages_cleaned'],
        crawl_stats['total_words'],
        crawl_stats['duration_seconds'],
        crawl_stats['pages_cleaned'] / max(crawl_stats['pages_crawled'], 1)
    ))
    
    conn.close()
    logger.success(f"Analytics updated for {app_id}")
    return {"status": "success"}

# ============================================
# Utility Functions
# ============================================

def split_into_chunks(text: str, chunk_size: int = 500) -> list:
    """Разбить текст на чанки"""
    words = text.split()
    chunks = []
    current_chunk = []
    current_size = 0
    
    for word in words:
        current_chunk.append(word)
        current_size += 1
        
        if current_size >= chunk_size:
            chunks.append(' '.join(current_chunk))
            current_chunk = []
            current_size = 0
    
    if current_chunk:
        chunks.append(' '.join(current_chunk))
    
    return chunks

# ============================================
# Flows
# ============================================

@flow(
    name="process-documentation",
    description="Полный цикл обработки документации: crawl → embed → analyze",
    task_runner=ConcurrentTaskRunner()
)
def process_documentation_flow(
    app_id: str,
    s3_bucket: str = None,
    s3_endpoint: str = None,
    pg_host: str = "postgres18",
    pg_database: str = "docagent",
    pg_user: str = "docagent",
    pg_password: str = None,
    chroma_url: str = "http://chromadb:8000",
    duckdb_path: str = "/app/data/analytics.duckdb"
):
    """
    Основной flow для обработки документации
    """
    logger.info(f"🚀 Starting documentation processing for {app_id}")
    
    # Конфигурация
    config = {
        's3_bucket': s3_bucket,
        's3_endpoint': s3_endpoint,
        'pg_host': pg_host,
        'pg_database': pg_database,
        'pg_user': pg_user,
        'pg_password': pg_password or os.getenv('PG_PASSWORD')
    }
    
    # Этап 1: Краулинг
    crawl_result = crawl_documentation(app_id, config)
    
    # Этап 2: Получение документов из БД
    conn = psycopg2.connect(
        host=pg_host,
        database=pg_database,
        user=pg_user,
        password=config['pg_password']
    )
    cur = conn.cursor()
    cur.execute("""
        SELECT id, url, title, s3_path 
        FROM documents 
        WHERE app_id = %s
    """, (app_id,))
    
    documents = [
        {
            'id': row[0],
            'url': row[1],
            'title': row[2],
            's3_path': row[3],
            'content': ''  # TODO: загрузить из S3
        }
        for row in cur.fetchall()
    ]
    cur.close()
    conn.close()
    
    # Этап 3: Генерация embeddings
    if documents:
        embed_result = generate_embeddings(app_id, documents, chroma_url)
    else:
        embed_result = {"chunks_added": 0}
    
    # Этап 4: Обновление аналитики
    analytics_result = update_analytics(app_id, crawl_result, duckdb_path)
    
    logger.success(f"✅ Documentation processing completed for {app_id}")
    
    return {
        "app_id": app_id,
        "crawl_result": crawl_result,
        "embed_result": embed_result,
        "analytics_result": analytics_result
    }

@flow(name="scheduled-crawl", description="Запланированный краулинг всех источников")
def scheduled_crawl_flow(apps: list = None):
    """
    Flow для регулярного краулинга всех источников
    """
    if not apps:
        apps = ['openspg', 'nocodb', 'python_docs', 'requesty']
    
    results = []
    for app_id in apps:
        try:
            result = process_documentation_flow(
                app_id=app_id,
                s3_bucket=os.getenv('S3_BUCKET'),
                s3_endpoint=os.getenv('S3_ENDPOINT')
            )
            results.append(result)
        except Exception as e:
            logger.error(f"Failed to process {app_id}: {e}")
            results.append({"app_id": app_id, "error": str(e)})
    
    return results

# ============================================
# Deployment
# ============================================

if __name__ == "__main__":
    # Пример запуска
    result = process_documentation_flow(
        app_id="openspg",
        s3_bucket=os.getenv('S3_BUCKET'),
        s3_endpoint=os.getenv('S3_ENDPOINT')
    )
    print(result)
