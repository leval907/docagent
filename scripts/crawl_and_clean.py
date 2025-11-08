#!/usr/bin/env python3
"""
Unified Pipeline: Crawl → Clean → Store
Запускает полный цикл обработки документации
"""
import asyncio
import hashlib
import os
import re
import yaml
import json
import boto3
from pathlib import Path
from typing import Set, List, Dict, Optional
from urllib.parse import urlparse, urljoin
from datetime import datetime

from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode
from loguru import logger
import click
import psycopg2
from psycopg2.extras import execute_values


class DocumentPipeline:
    """Полный пайплайн обработки документации"""
    
    def __init__(self, config_path: str = "config/sources.yaml"):
        self.config_path = config_path
        self.config = self._load_config()
        self.base_output_dir = Path(self.config.get('global', {}).get('output_base_dir', './knowledge_base'))
        
        # S3 клиент (опционально)
        self.s3_client = None
        self.s3_enabled = False
        
        # PostgreSQL connection (опционально)
        self.pg_conn = None
        self.pg_enabled = False
        
    def _load_config(self) -> dict:
        """Загрузка конфигурации"""
        with open(self.config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    
    def setup_s3(self, bucket: str, endpoint: Optional[str] = None, 
                 access_key: Optional[str] = None, secret_key: Optional[str] = None):
        """Настройка S3 клиента"""
        try:
            # Конфигурация для совместимости с разными S3-провайдерами
            from botocore.config import Config
            
            s3_config = Config(
                signature_version='s3v4',
                s3={
                    'addressing_style': 'path'  # Для Beget и других провайдеров
                }
            )
            
            if access_key and secret_key:
                self.s3_client = boto3.client(
                    's3',
                    endpoint_url=endpoint,
                    aws_access_key_id=access_key,
                    aws_secret_access_key=secret_key,
                    config=s3_config
                )
            else:
                # Используем credentials из окружения
                self.s3_client = boto3.client(
                    's3', 
                    endpoint_url=endpoint,
                    config=s3_config
                )
            
            self.s3_bucket = bucket
            self.s3_enabled = True
            logger.info(f"S3 enabled: bucket={bucket}, endpoint={endpoint}")
        except Exception as e:
            logger.warning(f"S3 setup failed: {e}")
            self.s3_enabled = False
    
    def setup_postgres(self, host: str, port: int, database: str, 
                      user: str, password: str):
        """Настройка PostgreSQL подключения"""
        try:
            self.pg_conn = psycopg2.connect(
                host=host,
                port=port,
                database=database,
                user=user,
                password=password
            )
            self.pg_enabled = True
            logger.info(f"PostgreSQL enabled: {host}:{port}/{database}")
            self._init_db_schema()
        except Exception as e:
            logger.warning(f"PostgreSQL setup failed: {e}")
            self.pg_enabled = False
    
    def _init_db_schema(self):
        """Инициализация схемы БД"""
        schema_sql = """
        CREATE TABLE IF NOT EXISTS documents (
            id SERIAL PRIMARY KEY,
            app_id VARCHAR(255) NOT NULL,
            url TEXT NOT NULL UNIQUE,
            title TEXT,
            file_path TEXT,
            s3_path TEXT,
            word_count INTEGER,
            file_hash VARCHAR(64),
            crawled_at TIMESTAMP,
            cleaned_at TIMESTAMP,
            uploaded_at TIMESTAMP,
            metadata JSONB,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        
        CREATE INDEX IF NOT EXISTS idx_documents_app_id ON documents(app_id);
        CREATE INDEX IF NOT EXISTS idx_documents_url ON documents(url);
        CREATE INDEX IF NOT EXISTS idx_documents_file_hash ON documents(file_hash);
        
        CREATE TABLE IF NOT EXISTS crawl_stats (
            id SERIAL PRIMARY KEY,
            app_id VARCHAR(255) NOT NULL,
            pages_crawled INTEGER,
            pages_cleaned INTEGER,
            pages_uploaded INTEGER,
            total_words INTEGER,
            started_at TIMESTAMP,
            finished_at TIMESTAMP,
            duration_seconds FLOAT,
            status VARCHAR(50),
            error_message TEXT
        );
        """
        
        with self.pg_conn.cursor() as cur:
            cur.execute(schema_sql)
            self.pg_conn.commit()
        
        logger.success("Database schema initialized")
    
    async def crawl_site(self, app_id: str, start_url: str, base_url: str,
                        output_dir: Path, max_depth: int = 3, 
                        max_pages: int = 100) -> Dict[str, str]:
        """
        Этап 1: Краулинг сайта
        Returns: Dict[url, markdown_content]
        """
        logger.info(f"📡 Stage 1: Crawling {app_id}")
        
        visited: Set[str] = set()
        to_visit: List[tuple] = [(start_url, 0)]
        results: Dict[str, str] = {}
        
        browser_config = BrowserConfig(headless=True, verbose=False)
        
        # Определяем тип сайта
        is_yuque = 'yuque.com' in base_url
        
        if is_yuque:
            crawl_config = CrawlerRunConfig(
                cache_mode=CacheMode.BYPASS,
                delay_before_return_html=6.0,
                page_timeout=90000,
                excluded_tags=['script', 'style', 'noscript', 'iframe'],
                remove_overlay_elements=True,
                word_count_threshold=5,
            )
        else:
            crawl_config = CrawlerRunConfig(
                cache_mode=CacheMode.BYPASS,
                excluded_tags=['script', 'style', 'nav', 'footer', 'aside', 'header'],
            )
        
        base_domain = urlparse(base_url).netloc
        crawler = AsyncWebCrawler(config=browser_config)
        
        try:
            await crawler.__aenter__()
            
            while to_visit and len(visited) < max_pages:
                current_url, depth = to_visit.pop(0)
                
                if current_url in visited or depth > max_depth:
                    continue
                
                if urlparse(current_url).netloc != base_domain:
                    continue
                
                if any(current_url.endswith(ext) for ext in ['.pdf', '.zip', '.jpg', '.png', '.gif', '.svg']):
                    continue
                
                visited.add(current_url)
                logger.info(f"  [{len(visited)}/{max_pages}] Depth {depth}: {current_url}")
                
                try:
                    result = await crawler.arun(url=current_url, config=crawl_config)
                    
                    if result.success and result.markdown:
                        results[current_url] = result.markdown
                        
                        # Извлекаем ссылки
                        internal_links = result.links.get('internal', [])
                        for link_obj in internal_links:
                            link_url = link_obj.get('href', '')
                            if link_url and link_url not in visited:
                                full_url = urljoin(current_url, link_url)
                                
                                if urlparse(full_url).netloc == base_domain:
                                    if is_yuque:
                                        base_path = '/'.join(urlparse(base_url).path.split('/')[:3])
                                        current_path = urlparse(full_url).path
                                        if current_path.startswith(base_path):
                                            to_visit.append((full_url, depth + 1))
                                    else:
                                        to_visit.append((full_url, depth + 1))
                    
                except Exception as e:
                    logger.error(f"  Error: {str(e)}")
                    continue
                
                await asyncio.sleep(0.5)
        
        finally:
            try:
                await crawler.__aexit__(None, None, None)
            except Exception as e:
                logger.warning(f"Crawler cleanup error: {e}")
        
        logger.success(f"✅ Crawled {len(results)} pages")
        return results
    
    def clean_markdown(self, content: str) -> str:
        """
        Этап 2: Очистка markdown
        """
        # Паттерны для удаления
        removal_patterns = [
            r'搜索⌘ \+ [JK]',
            r'首页\n目录',
            r'大纲',
            r'\[免费使用\].*?\)',
            r'若有收获，就点个赞吧',
            r'IP 属地.*?\n',
            r'举报\n?',
            r'\[[\u4e00-\u9fa5]+\]\(https://.*?yuque\.com/.*?\)',
            r'、\[[\u4e00-\u9fa5]+\]\(https://.*?yuque\.com/.*?\)',
            r'\d{2}-\d{2} \d{2}:\d{2}',
            r'\n{3,}',
            r'​',  # Zero-width space
        ]
        
        # Удаляем паттерны
        for pattern in removal_patterns:
            content = re.sub(pattern, '', content, flags=re.MULTILINE)
        
        # Замены
        replacements = {
            r'&amp;': '&',
            r'&lt;': '<',
            r'&gt;': '>',
            r'&nbsp;': ' ',
            r'  +': ' ',
        }
        
        for pattern, replacement in replacements.items():
            content = re.sub(pattern, replacement, content)
        
        # Нормализация
        content = content.strip()
        content = re.sub(r'\n{3,}', '\n\n', content)
        
        return content
    
    def save_markdown(self, app_id: str, url: str, content: str, 
                     output_dir: Path) -> Dict:
        """
        Сохранение markdown с метаданными
        """
        # Генерируем имя файла
        url_hash = hashlib.md5(url.encode()).hexdigest()[:16]
        path_parts = urlparse(url).path.strip('/').split('/')
        filename = '-'.join(path_parts[-3:]) if len(path_parts) >= 3 else path_parts[-1] if path_parts else url_hash
        filename = re.sub(r'[^\w\-.]', '-', filename)
        filename = f"{filename}.md"
        
        file_path = output_dir / filename
        
        # Очищаем контент
        cleaned_content = self.clean_markdown(content)
        word_count = len(cleaned_content.split())
        
        # YAML метаданные
        metadata = {
            'source': url,
            'title': filename.replace('.md', ''),
            'crawled_at': datetime.utcnow().isoformat(),
            'file_hash': hashlib.md5(cleaned_content.encode()).hexdigest(),
            'word_count': word_count,
            'cleaned': True
        }
        
        # Формируем файл
        yaml_front = yaml.dump(metadata, allow_unicode=True)
        final_content = f"---\n{yaml_front}---\n\n{cleaned_content}"
        
        # Сохраняем
        output_dir.mkdir(parents=True, exist_ok=True)
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(final_content)
        
        return {
            'file_path': str(file_path),
            'filename': filename,
            'metadata': metadata
        }
    
    def upload_to_s3(self, file_path: str, s3_key: str) -> Optional[str]:
        """
        Этап 3: Загрузка в S3
        """
        if not self.s3_enabled:
            return None
        
        try:
            import hashlib
            import base64
            
            # Читаем файл в бинарном режиме
            with open(file_path, 'rb') as f:
                file_content = f.read()
            
            # Вычисляем SHA256 и кодируем в base64 для Beget S3
            sha256_digest = hashlib.sha256(file_content).digest()
            checksum_sha256 = base64.b64encode(sha256_digest).decode()
            
            self.s3_client.put_object(
                Bucket=self.s3_bucket,
                Key=s3_key,
                Body=file_content,
                ContentType='text/markdown; charset=utf-8',
                ChecksumSHA256=checksum_sha256
            )
            
            s3_url = f"s3://{self.s3_bucket}/{s3_key}"
            logger.debug(f"  Uploaded to S3: {s3_key}")
            return s3_url
            
        except Exception as e:
            logger.error(f"  S3 upload failed: {e}")
            return None
    
    def save_to_postgres(self, app_id: str, documents: List[Dict]):
        """
        Этап 4: Сохранение индекса в PostgreSQL
        """
        if not self.pg_enabled:
            return
        
        try:
            with self.pg_conn.cursor() as cur:
                # Prepare data
                values = [
                    (
                        app_id,
                        doc['url'],
                        doc['metadata']['title'],
                        doc['file_path'],
                        doc.get('s3_path'),
                        doc['metadata']['word_count'],
                        doc['metadata']['file_hash'],
                        doc['metadata']['crawled_at'],
                        doc['metadata']['crawled_at'],  # cleaned_at
                        doc.get('uploaded_at'),
                        json.dumps(doc['metadata'])
                    )
                    for doc in documents
                ]
                
                # Upsert
                insert_sql = """
                    INSERT INTO documents 
                    (app_id, url, title, file_path, s3_path, word_count, 
                     file_hash, crawled_at, cleaned_at, uploaded_at, metadata)
                    VALUES %s
                    ON CONFLICT (url) 
                    DO UPDATE SET
                        title = EXCLUDED.title,
                        file_path = EXCLUDED.file_path,
                        s3_path = EXCLUDED.s3_path,
                        word_count = EXCLUDED.word_count,
                        file_hash = EXCLUDED.file_hash,
                        cleaned_at = EXCLUDED.cleaned_at,
                        uploaded_at = EXCLUDED.uploaded_at,
                        metadata = EXCLUDED.metadata,
                        updated_at = CURRENT_TIMESTAMP
                """
                
                execute_values(cur, insert_sql, values)
                self.pg_conn.commit()
                
            logger.success(f"  Saved {len(documents)} documents to PostgreSQL")
            
        except Exception as e:
            logger.error(f"  PostgreSQL save failed: {e}")
            self.pg_conn.rollback()
    
    def save_stats(self, app_id: str, stats: Dict):
        """Сохранение статистики краула"""
        if not self.pg_enabled:
            return
        
        try:
            with self.pg_conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO crawl_stats 
                    (app_id, pages_crawled, pages_cleaned, pages_uploaded, 
                     total_words, started_at, finished_at, duration_seconds, status)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    app_id,
                    stats['pages_crawled'],
                    stats['pages_cleaned'],
                    stats['pages_uploaded'],
                    stats['total_words'],
                    stats['started_at'],
                    stats['finished_at'],
                    stats['duration_seconds'],
                    stats['status']
                ))
                self.pg_conn.commit()
        except Exception as e:
            logger.error(f"Stats save failed: {e}")
    
    async def process_app(self, app_id: str, app_config: Dict) -> Dict:
        """
        Полный процесс обработки приложения
        """
        start_time = datetime.utcnow()
        
        logger.info("=" * 70)
        logger.info(f"🚀 Processing: {app_config.get('name', app_id)}")
        logger.info("=" * 70)
        
        output_dir = self.base_output_dir / app_id
        
        # Этап 1: Краулинг
        try:
            crawled_pages = await self.crawl_site(
                app_id=app_id,
                start_url=app_config['url'],
                base_url=app_config['url'],
                output_dir=output_dir,
                max_depth=app_config.get('depth', 3),
                max_pages=app_config.get('max_pages', 100)
            )
        except Exception as e:
            logger.error(f"Crawling failed: {e}")
            return {'status': 'error', 'error': str(e)}
        
        # Этап 2 & 3: Очистка и сохранение
        logger.info(f"🧹 Stage 2: Cleaning & Saving")
        documents = []
        total_words = 0
        
        for url, content in crawled_pages.items():
            try:
                doc_info = self.save_markdown(app_id, url, content, output_dir)
                doc_info['url'] = url
                
                # Этап 3: Upload to S3
                if self.s3_enabled:
                    s3_key = f"{app_id}/{doc_info['filename']}"
                    s3_path = self.upload_to_s3(doc_info['file_path'], s3_key)
                    doc_info['s3_path'] = s3_path
                    doc_info['uploaded_at'] = datetime.utcnow().isoformat()
                
                documents.append(doc_info)
                total_words += doc_info['metadata']['word_count']
                
            except Exception as e:
                logger.error(f"  Failed to process {url}: {e}")
                continue
        
        logger.success(f"✅ Cleaned and saved {len(documents)} documents")
        
        # Этап 4: Сохранение в PostgreSQL
        if self.pg_enabled:
            logger.info(f"💾 Stage 3: Saving to PostgreSQL")
            self.save_to_postgres(app_id, documents)
        
        # Статистика
        end_time = datetime.utcnow()
        duration = (end_time - start_time).total_seconds()
        
        stats = {
            'app_id': app_id,
            'pages_crawled': len(crawled_pages),
            'pages_cleaned': len(documents),
            'pages_uploaded': len([d for d in documents if d.get('s3_path')]),
            'total_words': total_words,
            'started_at': start_time,
            'finished_at': end_time,
            'duration_seconds': duration,
            'status': 'success'
        }
        
        self.save_stats(app_id, stats)
        
        # Итоговый отчет
        logger.info("")
        logger.info("=" * 70)
        logger.info(f"📊 Summary for {app_id}")
        logger.info("=" * 70)
        logger.success(f"  Pages crawled:  {stats['pages_crawled']}")
        logger.success(f"  Pages cleaned:  {stats['pages_cleaned']}")
        if self.s3_enabled:
            logger.success(f"  Uploaded to S3: {stats['pages_uploaded']}")
        if self.pg_enabled:
            logger.success(f"  Saved to DB:    {stats['pages_cleaned']}")
        logger.success(f"  Total words:    {stats['total_words']:,}")
        logger.success(f"  Duration:       {duration:.1f}s")
        logger.info("=" * 70)
        
        return stats


@click.command()
@click.option('--app', required=True, help='App ID to process')
@click.option('--s3-bucket', help='S3 bucket name')
@click.option('--s3-endpoint', help='S3 endpoint URL')
@click.option('--s3-access-key', envvar='AWS_ACCESS_KEY_ID', help='S3 access key')
@click.option('--s3-secret-key', envvar='AWS_SECRET_ACCESS_KEY', help='S3 secret key')
@click.option('--pg-host', envvar='PG_HOST', help='PostgreSQL host')
@click.option('--pg-port', envvar='PG_PORT', default=5432, help='PostgreSQL port')
@click.option('--pg-database', envvar='PG_DATABASE', help='PostgreSQL database')
@click.option('--pg-user', envvar='PG_USER', help='PostgreSQL user')
@click.option('--pg-password', envvar='PG_PASSWORD', help='PostgreSQL password')
def main(app: str, s3_bucket: Optional[str], s3_endpoint: Optional[str],
         s3_access_key: Optional[str], s3_secret_key: Optional[str],
         pg_host: Optional[str], pg_port: int, pg_database: Optional[str],
         pg_user: Optional[str], pg_password: Optional[str]):
    """
    Unified pipeline: Crawl → Clean → Upload → Index
    
    Example:
        python crawl_and_clean.py --app openspg
        
        python crawl_and_clean.py --app openspg \\
            --s3-bucket my-docs \\
            --s3-endpoint https://s3.amazonaws.com \\
            --pg-host localhost \\
            --pg-database docagent \\
            --pg-user postgres
    """
    
    # Инициализация
    pipeline = DocumentPipeline()
    
    # Настройка S3
    if s3_bucket:
        pipeline.setup_s3(
            bucket=s3_bucket,
            endpoint=s3_endpoint,
            access_key=s3_access_key,
            secret_key=s3_secret_key
        )
    
    # Настройка PostgreSQL
    if pg_host and pg_database and pg_user:
        pipeline.setup_postgres(
            host=pg_host,
            port=pg_port,
            database=pg_database,
            user=pg_user,
            password=pg_password or ''
        )
    
    # Загружаем конфигурацию приложения
    config = pipeline.config.get('apps', {}).get(app)
    if not config:
        logger.error(f"App '{app}' not found in config")
        return
    
    if not config.get('enabled', False):
        logger.error(f"App '{app}' is disabled")
        return
    
    # Запускаем процесс
    asyncio.run(pipeline.process_app(app, config))
    
    # Закрываем соединения
    if pipeline.pg_conn:
        pipeline.pg_conn.close()


if __name__ == "__main__":
    main()
