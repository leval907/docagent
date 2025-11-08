-- DocAgent Database Initialization Script
-- PostgreSQL 18 + pgvector

-- Создание расширения pgvector для векторного поиска
CREATE EXTENSION IF NOT EXISTS vector;

-- Таблица документов
CREATE TABLE IF NOT EXISTS documents (
    id SERIAL PRIMARY KEY,
    app_id VARCHAR(50) NOT NULL,
    url TEXT NOT NULL UNIQUE,
    title TEXT,
    s3_path TEXT,
    file_hash VARCHAR(64),
    word_count INTEGER,
    metadata JSONB,
    crawled_at TIMESTAMP,
    uploaded_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Таблица статистики краулинга
CREATE TABLE IF NOT EXISTS crawl_stats (
    id SERIAL PRIMARY KEY,
    app_id VARCHAR(50) NOT NULL,
    pages_crawled INTEGER,
    pages_cleaned INTEGER,
    pages_uploaded INTEGER,
    total_words INTEGER,
    duration_seconds FLOAT,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Таблица для векторных эмбеддингов (pgvector)
CREATE TABLE IF NOT EXISTS document_embeddings (
    id SERIAL PRIMARY KEY,
    document_id INTEGER REFERENCES documents(id) ON DELETE CASCADE,
    chunk_index INTEGER NOT NULL,
    chunk_text TEXT NOT NULL,
    embedding vector(1536),  -- OpenAI ada-002: 1536 dimensions
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(document_id, chunk_index)
);

-- Индексы для производительности
CREATE INDEX IF NOT EXISTS idx_documents_app_id ON documents(app_id);
CREATE INDEX IF NOT EXISTS idx_documents_url ON documents(url);
CREATE INDEX IF NOT EXISTS idx_documents_created_at ON documents(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_crawl_stats_app_id ON crawl_stats(app_id);
CREATE INDEX IF NOT EXISTS idx_crawl_stats_created_at ON crawl_stats(created_at DESC);

-- HNSW индекс для быстрого векторного поиска (cosine distance)
CREATE INDEX IF NOT EXISTS idx_embeddings_vector ON document_embeddings 
USING hnsw (embedding vector_cosine_ops);

-- Индекс для связи эмбеддингов с документами
CREATE INDEX IF NOT EXISTS idx_embeddings_document_id ON document_embeddings(document_id);

-- Функция для обновления updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Триггер для автоматического обновления updated_at
CREATE TRIGGER update_documents_updated_at BEFORE UPDATE ON documents
FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Создание пользователя для read-only доступа (опционально)
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'docagent_readonly') THEN
        CREATE ROLE docagent_readonly WITH LOGIN PASSWORD 'readonly_pass_2025';
    END IF;
END
$$;

-- Права для read-only пользователя
GRANT CONNECT ON DATABASE docagent TO docagent_readonly;
GRANT USAGE ON SCHEMA public TO docagent_readonly;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO docagent_readonly;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO docagent_readonly;

-- Вывод успешной инициализации
DO $$
BEGIN
    RAISE NOTICE '✅ DocAgent database initialized successfully!';
    RAISE NOTICE '📊 Tables: documents, crawl_stats, document_embeddings';
    RAISE NOTICE '🧠 pgvector extension enabled for vector search';
    RAISE NOTICE '🔍 HNSW index created for fast similarity search';
END
$$;
