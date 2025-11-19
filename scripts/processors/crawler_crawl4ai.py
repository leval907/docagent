#!/usr/bin/env python3
"""
DocAgent Crawler using Crawl4AI
Supports JavaScript-rendered sites
"""
import asyncio
import hashlib
import os
import re
import yaml
from pathlib import Path
from typing import Set, List, Dict
from urllib.parse import urlparse, urljoin
from datetime import datetime

from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode
from loguru import logger
import click


class DocAgentCrawl4AI:
    def __init__(self, config_path: str = "config/sources.yaml"):
        self.config_path = config_path
        self.config = self._load_config()
        self.base_output_dir = Path(self.config.get('global', {}).get('output_base_dir', './knowledge_base'))
        
    def _load_config(self) -> dict:
        """Загрузка конфигурации из YAML"""
        with open(self.config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    
    def _get_enabled_apps(self) -> List[Dict]:
        """Получить список активных приложений"""
        apps = []
        for app_id, app_config in self.config.get('apps', {}).items():
            if app_config.get('enabled', False):
                apps.append({
                    'id': app_id,
                    **app_config
                })
        return apps
    
    async def crawl_recursive(
        self, 
        start_url: str, 
        base_url: str,
        output_dir: Path,
        max_depth: int = 3,
        max_pages: int = 100
    ) -> Dict[str, str]:
        """
        Рекурсивный обход сайта
        
        Returns:
            Dict[url, markdown_content]
        """
        visited: Set[str] = set()
        to_visit: List[tuple] = [(start_url, 0)]  # (url, depth)
        results: Dict[str, str] = {}
        
        browser_config = BrowserConfig(
            headless=True,
            verbose=False  # Отключаем verbose чтобы избежать проблем с Unicode в Windows
        )
        
        # Специальная конфигурация для разных типов сайтов
        is_yuque = 'yuque.com' in base_url
        
        if is_yuque:
            # Yuque требует больше времени для загрузки контента
            crawl_config = CrawlerRunConfig(
                cache_mode=CacheMode.BYPASS,
                delay_before_return_html=6.0,  # Компромисс между скоростью и полнотой
                page_timeout=90000,  # 90 секунд
                # Исключаем навигацию и служебные элементы
                excluded_tags=['script', 'style', 'noscript', 'iframe'],
                # НЕ используем css_selector - он блокирует извлечение ссылок
                # Удаляем оверлеи и попапы
                remove_overlay_elements=True,
                # Убираем пустые строки
                word_count_threshold=5,
            )
        else:
            # Стандартная конфигурация
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
                
                # Пропускаем уже посещённые
                if current_url in visited:
                    continue
                
                # Проверяем глубину
                if depth > max_depth:
                    continue
                
                # Проверяем домен
                if urlparse(current_url).netloc != base_domain:
                    continue
                
                # Пропускаем файлы (не HTML)
                if any(current_url.endswith(ext) for ext in ['.pdf', '.zip', '.jpg', '.png', '.gif', '.svg']):
                    continue
                
                visited.add(current_url)
                logger.info(f"[{len(visited)}/{max_pages}] Depth {depth}: {current_url}")
                
                try:
                    result = await crawler.arun(url=current_url, config=crawl_config)
                    
                    if result.success and result.markdown:
                        # Сохраняем markdown
                        results[current_url] = result.markdown
                        
                        # Извлекаем внутренние ссылки
                        internal_links = result.links.get('internal', [])
                        logger.info(f"Found {len(internal_links)} internal links")
                        
                        for link_obj in internal_links:
                            link_url = link_obj.get('href', '')
                            if link_url and link_url not in visited:
                                # Нормализуем URL
                                full_url = urljoin(current_url, link_url)
                                
                                # Проверяем, что это тот же домен
                                if urlparse(full_url).netloc == base_domain:
                                    # Для yuque проверяем что это тот же раздел документации
                                    if is_yuque:
                                        # Извлекаем базовый путь (например /ndx6g9/0.8.en)
                                        base_path = '/'.join(urlparse(base_url).path.split('/')[:3])
                                        current_path = urlparse(full_url).path
                                        if current_path.startswith(base_path):
                                            logger.debug(f"Adding to queue: {full_url}")
                                            to_visit.append((full_url, depth + 1))
                                        else:
                                            logger.debug(f"Skipping (wrong base path): {full_url}")
                                    else:
                                        to_visit.append((full_url, depth + 1))
                                else:
                                    logger.debug(f"Skipping (wrong domain): {full_url}")
                    else:
                        logger.warning(f"Failed to crawl {current_url}: {result.error_message}")
                        
                except Exception as e:
                    logger.error(f"Error crawling {current_url}: {str(e)}")
                    # При ошибке пропускаем страницу и продолжаем
                    continue
                
                # Небольшая задержка между запросами
                await asyncio.sleep(0.5)
        
        finally:
            # Безопасное закрытие краулера
            try:
                await crawler.__aexit__(None, None, None)
            except Exception as e:
                logger.warning(f"Error closing crawler: {e}")
        
        return results
    
    def _save_markdown(self, url: str, content: str, output_dir: Path, metadata: dict = None):
        """Сохранение markdown файла с метаданными"""
        # Генерируем имя файла из URL
        parsed = urlparse(url)
        path_parts = [p for p in parsed.path.split('/') if p]
        
        if not path_parts:
            filename = 'index.md'
        else:
            filename = '-'.join(path_parts) + '.md'
        
        # Убираем небезопасные символы
        filename = re.sub(r'[^\w\-.]', '_', filename)
        
        filepath = output_dir / filename
        
        # Добавляем YAML front matter
        yaml_front_matter = {
            'title': metadata.get('title', filename.replace('.md', '').replace('-', ' ').title()),
            'source': url,
            'crawled_at': datetime.now().isoformat(),
            'file_hash': hashlib.md5(content.encode()).hexdigest(),
            'word_count': len(content.split()),
        }
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write('---\n')
            yaml.dump(yaml_front_matter, f, allow_unicode=True)
            f.write('---\n\n')
            f.write(content)
        
        return filepath
    
    async def crawl_app(self, app_id: str):
        """Краулинг конкретного приложения"""
        apps = self._get_enabled_apps()
        app = next((a for a in apps if a['id'] == app_id), None)
        
        if not app:
            logger.error(f"App '{app_id}' not found or not enabled")
            return
        
        logger.info(f"🚀 Starting crawl for: {app.get('name', app_id)}")
        logger.info(f"   URL: {app['url']}")
        
        output_dir = self.base_output_dir / app_id
        output_dir.mkdir(parents=True, exist_ok=True)
        
        max_depth = app.get('depth', 2)
        max_pages = app.get('max_pages', 100)
        
        # Рекурсивный краулинг
        results = await self.crawl_recursive(
            start_url=app['url'],
            base_url=app['url'],
            output_dir=output_dir,
            max_depth=max_depth,
            max_pages=max_pages
        )
        
        # Сохраняем результаты
        logger.info(f"💾 Saving {len(results)} pages...")
        for url, markdown in results.items():
            self._save_markdown(url, markdown, output_dir, {'title': url.split('/')[-1]})
        
        logger.success(f"✅ Crawl completed: {len(results)} pages saved to {output_dir}")


@click.command()
@click.option('--app', required=True, help='App ID to crawl (from sources.yaml)')
@click.option('--config', default='config/sources.yaml', help='Path to config file')
def main(app: str, config: str):
    """DocAgent Crawler using Crawl4AI"""
    crawler = DocAgentCrawl4AI(config_path=config)
    asyncio.run(crawler.crawl_app(app))


if __name__ == "__main__":
    main()
