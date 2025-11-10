#!/usr/bin/env python3
"""
Легковесный пайплайн для экспериментов с chunking + embedding + поиск
Использует только SQLite и sentence-transformers, без Docker
"""

import sqlite3
import hashlib
import json
import asyncio
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional, Tuple
import re

# Для embeddings
try:
    from sentence_transformers import SentenceTransformer
    import numpy as np
except ImportError:
    print("⚠️  Установите: pip install sentence-transformers")
    exit(1)

# Для краулинга (опционально, можно использовать готовые файлы)
try:
    from crawl4ai import AsyncWebCrawler
except ImportError:
    print("⚠️  Crawl4AI не установлен, будет работать только с существующими файлами")
    AsyncWebCrawler = None


class DocumentPipelineLite:
    """Легковесный пайплайн для экспериментов"""
    
    def __init__(
        self,
        db_path: str = "docagent_lite.db",
        model_name: str = "all-MiniLM-L6-v2",  # Легкая модель, 384 dim
        chunk_size: int = 500,  # Слов на chunk
        chunk_overlap: int = 50  # Слов overlap
    ):
        self.db_path = Path(db_path)
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        
        # Инициализация БД
        self.init_database()
        
        # Загрузка модели для embeddings
        print(f"📦 Загрузка модели {model_name}...")
        self.model = SentenceTransformer(model_name)
        self.embedding_dim = self.model.get_sentence_embedding_dimension()
        print(f"✅ Модель загружена, размерность: {self.embedding_dim}")
    
    def init_database(self):
        """Создание таблиц в SQLite"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Таблица документов
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS documents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                url TEXT UNIQUE NOT NULL,
                title TEXT,
                app_id TEXT,
                content TEXT,
                word_count INTEGER,
                chunk_count INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Таблица chunks с embeddings
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS chunks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                document_id INTEGER NOT NULL,
                chunk_index INTEGER NOT NULL,
                chunk_text TEXT NOT NULL,
                word_count INTEGER,
                embedding BLOB,  -- Хранение как pickle/json
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE
            )
        """)
        
        # Индексы для быстрого поиска
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_documents_app 
            ON documents(app_id)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_chunks_document 
            ON chunks(document_id)
        """)
        
        conn.commit()
        conn.close()
        print(f"✅ База данных инициализирована: {self.db_path}")
    
    def clean_markdown(self, content: str) -> str:
        """Очистка markdown от UI элементов"""
        patterns = [
            (r'\[下一页\]\([^)]+\)', ''),  # Навигация
            (r'!\[.*?\]\(.*?\)', ''),  # Изображения
            (r'\[.*?\]\(javascript:.*?\)', ''),  # JS ссылки
            (r'#+\s*目录.*?(?=\n##|\Z)', '', re.DOTALL),  # Оглавление
            (r'\n{3,}', '\n\n'),  # Множественные переносы
        ]
        
        for pattern, replacement, *flags in patterns:
            flag = flags[0] if flags else 0
            content = re.sub(pattern, replacement, content, flags=flag)
        
        return content.strip()
    
    def chunk_text(self, text: str) -> List[Dict[str, any]]:
        """Разбивка текста на chunks с overlap"""
        words = text.split()
        chunks = []
        
        for i in range(0, len(words), self.chunk_size - self.chunk_overlap):
            chunk_words = words[i:i + self.chunk_size]
            chunk_text = ' '.join(chunk_words)
            
            if len(chunk_words) < 50:  # Пропускаем слишком короткие
                continue
            
            chunks.append({
                'index': len(chunks),
                'text': chunk_text,
                'word_count': len(chunk_words)
            })
        
        return chunks
    
    def generate_embeddings(self, texts: List[str]) -> np.ndarray:
        """Генерация embeddings для списка текстов"""
        return self.model.encode(texts, show_progress_bar=True)
    
    def save_document(
        self,
        url: str,
        title: str,
        content: str,
        app_id: str = "default"
    ) -> int:
        """Сохранение документа с chunking и embeddings"""
        
        # Очистка контента
        clean_content = self.clean_markdown(content)
        word_count = len(clean_content.split())
        
        # Chunking
        chunks = self.chunk_text(clean_content)
        print(f"📄 Документ разбит на {len(chunks)} chunks")
        
        # Генерация embeddings
        chunk_texts = [c['text'] for c in chunks]
        embeddings = self.generate_embeddings(chunk_texts)
        print(f"🧠 Embeddings сгенерированы: {embeddings.shape}")
        
        # Сохранение в БД
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Сохранение документа
            cursor.execute("""
                INSERT OR REPLACE INTO documents 
                (url, title, app_id, content, word_count, chunk_count, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """, (url, title, app_id, clean_content, word_count, len(chunks)))
            
            doc_id = cursor.lastrowid
            
            # Удаление старых chunks если обновление
            cursor.execute("DELETE FROM chunks WHERE document_id = ?", (doc_id,))
            
            # Сохранение chunks с embeddings
            for chunk, embedding in zip(chunks, embeddings):
                # Сериализация embedding как JSON
                embedding_json = json.dumps(embedding.tolist())
                
                cursor.execute("""
                    INSERT INTO chunks 
                    (document_id, chunk_index, chunk_text, word_count, embedding)
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    doc_id,
                    chunk['index'],
                    chunk['text'],
                    chunk['word_count'],
                    embedding_json
                ))
            
            conn.commit()
            print(f"✅ Документ сохранен: ID={doc_id}, chunks={len(chunks)}")
            return doc_id
            
        finally:
            conn.close()
    
    def cosine_similarity(self, a: np.ndarray, b: np.ndarray) -> float:
        """Косинусное сходство между векторами"""
        return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))
    
    def search(
        self,
        query: str,
        app_id: Optional[str] = None,
        limit: int = 10,
        min_similarity: float = 0.3
    ) -> List[Dict]:
        """Векторный поиск по chunks"""
        
        # Генерация embedding для запроса
        query_embedding = self.model.encode([query])[0]
        
        # Получение всех chunks (можно оптимизировать фильтрацией по app_id)
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        if app_id:
            cursor.execute("""
                SELECT c.id, c.document_id, c.chunk_index, c.chunk_text, 
                       c.embedding, d.title, d.url, d.app_id
                FROM chunks c
                JOIN documents d ON c.document_id = d.id
                WHERE d.app_id = ?
            """, (app_id,))
        else:
            cursor.execute("""
                SELECT c.id, c.document_id, c.chunk_index, c.chunk_text, 
                       c.embedding, d.title, d.url, d.app_id
                FROM chunks c
                JOIN documents d ON c.document_id = d.id
            """)
        
        results = []
        for row in cursor.fetchall():
            chunk_id, doc_id, chunk_idx, chunk_text, embedding_json, title, url, app = row
            
            # Десериализация embedding
            chunk_embedding = np.array(json.loads(embedding_json))
            
            # Вычисление similarity
            similarity = self.cosine_similarity(query_embedding, chunk_embedding)
            
            if similarity >= min_similarity:
                results.append({
                    'chunk_id': chunk_id,
                    'document_id': doc_id,
                    'chunk_index': chunk_idx,
                    'title': title,
                    'url': url,
                    'app_id': app,
                    'chunk_text': chunk_text,
                    'similarity': float(similarity)
                })
        
        conn.close()
        
        # Сортировка по similarity
        results.sort(key=lambda x: x['similarity'], reverse=True)
        
        return results[:limit]
    
    async def crawl_and_process(
        self,
        url: str,
        app_id: str = "default"
    ):
        """Краулинг страницы и обработка"""
        if AsyncWebCrawler is None:
            print("❌ Crawl4AI не установлен")
            return
        
        print(f"🕷️  Краулинг: {url}")
        
        async with AsyncWebCrawler(verbose=False) as crawler:
            result = await crawler.arun(
                url=url,
                bypass_cache=True,
                wait_for="networkidle",
                delay_before_return_html=3.0
            )
            
            if result.success:
                self.save_document(
                    url=url,
                    title=result.title or "Untitled",
                    content=result.markdown,
                    app_id=app_id
                )
            else:
                print(f"❌ Ошибка краулинга: {result.error_message}")
    
    def load_from_file(
        self,
        file_path: str,
        url: str = None,
        title: str = None,
        app_id: str = "default"
    ):
        """Загрузка документа из файла"""
        path = Path(file_path)
        
        if not path.exists():
            print(f"❌ Файл не найден: {file_path}")
            return
        
        content = path.read_text(encoding='utf-8')
        
        self.save_document(
            url=url or f"file://{path.absolute()}",
            title=title or path.stem,
            content=content,
            app_id=app_id
        )
    
    def stats(self) -> Dict:
        """Статистика по базе"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Документы по приложениям
        cursor.execute("""
            SELECT app_id, COUNT(*) as docs, SUM(word_count) as words, SUM(chunk_count) as chunks
            FROM documents
            GROUP BY app_id
        """)
        
        apps = []
        for row in cursor.fetchall():
            apps.append({
                'app_id': row[0],
                'documents': row[1],
                'words': row[2],
                'chunks': row[3]
            })
        
        # Общая статистика
        cursor.execute("SELECT COUNT(*) FROM documents")
        total_docs = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM chunks")
        total_chunks = cursor.fetchone()[0]
        
        conn.close()
        
        return {
            'total_documents': total_docs,
            'total_chunks': total_chunks,
            'apps': apps
        }


def main():
    """Пример использования"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Легковесный пайплайн для экспериментов")
    parser.add_argument("--db", default="docagent_lite.db", help="Путь к SQLite БД")
    parser.add_argument("--model", default="all-MiniLM-L6-v2", help="Модель для embeddings")
    
    subparsers = parser.add_subparsers(dest='command', help='Команды')
    
    # Команда: load
    load_parser = subparsers.add_parser('load', help='Загрузка файла')
    load_parser.add_argument("file", help="Путь к markdown файлу")
    load_parser.add_argument("--app", default="default", help="ID приложения")
    load_parser.add_argument("--title", help="Заголовок документа")
    
    # Команда: crawl
    crawl_parser = subparsers.add_parser('crawl', help='Краулинг URL')
    crawl_parser.add_argument("url", help="URL для краулинга")
    crawl_parser.add_argument("--app", default="default", help="ID приложения")
    
    # Команда: search
    search_parser = subparsers.add_parser('search', help='Поиск по запросу')
    search_parser.add_argument("query", help="Поисковый запрос")
    search_parser.add_argument("--app", help="Фильтр по приложению")
    search_parser.add_argument("--limit", type=int, default=5, help="Количество результатов")
    
    # Команда: stats
    stats_parser = subparsers.add_parser('stats', help='Статистика по БД')
    
    args = parser.parse_args()
    
    # Инициализация pipeline
    pipeline = DocumentPipelineLite(
        db_path=args.db,
        model_name=args.model
    )
    
    if args.command == 'load':
        pipeline.load_from_file(
            file_path=args.file,
            title=args.title,
            app_id=args.app
        )
        
    elif args.command == 'crawl':
        asyncio.run(pipeline.crawl_and_process(
            url=args.url,
            app_id=args.app
        ))
        
    elif args.command == 'search':
        results = pipeline.search(
            query=args.query,
            app_id=args.app,
            limit=args.limit
        )
        
        print(f"\n🔍 Найдено результатов: {len(results)}\n")
        for i, result in enumerate(results, 1):
            print(f"{i}. [{result['title']}] ({result['similarity']:.3f})")
            print(f"   URL: {result['url']}")
            print(f"   App: {result['app_id']}")
            print(f"   Текст: {result['chunk_text'][:200]}...")
            print()
        
    elif args.command == 'stats':
        stats = pipeline.stats()
        print(f"\n📊 Статистика")
        print(f"Документов: {stats['total_documents']}")
        print(f"Chunks: {stats['total_chunks']}")
        print(f"\nПо приложениям:")
        for app in stats['apps']:
            print(f"  {app['app_id']}: {app['documents']} docs, {app['words']} words, {app['chunks']} chunks")
    
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
