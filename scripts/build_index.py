#!/usr/bin/env python3
"""
DocAgent Indexer
Создаёт JSON индексы для быстрого поиска по документации
"""

import os
import sys
import json
import yaml
import argparse
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional
from loguru import logger

# Настройка логирования
logger.remove()
logger.add(sys.stderr, format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>")


class DocAgentIndexer:
    """Класс для создания индексов документации"""
    
    def __init__(self, base_dir: str = "knowledge_base"):
        """
        Инициализация
        
        Args:
            base_dir: Базовая директория с markdown файлами
        """
        self.base_dir = Path(base_dir)
        
        logger.info(f"DocAgentIndexer initialized")
        logger.info(f"Base dir: {self.base_dir.absolute()}")
    
    def parse_yaml_frontmatter(self, file_path: Path) -> Optional[Dict]:
        """
        Извлечь YAML front matter из markdown файла
        
        Args:
            file_path: Путь к файлу
            
        Returns:
            Словарь с метаданными или None
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Проверить наличие front matter
            if not content.startswith('---\n'):
                return None
            
            # Разделить на части
            parts = content.split('---\n', 2)
            if len(parts) < 3:
                return None
            
            # Парсить YAML
            metadata = yaml.safe_load(parts[1])
            return metadata
            
        except Exception as e:
            logger.error(f"Error parsing {file_path.name}: {e}")
            return None
    
    def build_app_index(self, app_name: str, output_file: Optional[str] = None) -> Dict:
        """
        Создать индекс для одного приложения
        
        Args:
            app_name: Имя приложения
            output_file: Путь для сохранения JSON (опционально)
            
        Returns:
            Словарь с индексом
        """
        app_dir = self.base_dir / app_name
        
        if not app_dir.exists():
            logger.error(f"App directory not found: {app_dir}")
            return {}
        
        logger.info(f"🔍 Building index for: {app_name}")
        
        # Найти все markdown файлы
        md_files = list(app_dir.glob("*.md"))
        logger.info(f"   Found: {len(md_files)} markdown files")
        
        # Собрать метаданные
        pages = []
        total_words = 0
        categories = {}
        tags_set = set()
        
        for md_file in md_files:
            metadata = self.parse_yaml_frontmatter(md_file)
            
            if not metadata:
                logger.warning(f"No metadata: {md_file.name}")
                continue
            
            # Добавить в список страниц
            pages.append(metadata)
            
            # Подсчитать статистику
            total_words += metadata.get('word_count', 0)
            
            # Категории
            category = metadata.get('category', 'uncategorized')
            categories[category] = categories.get(category, 0) + 1
            
            # Теги
            for tag in metadata.get('tags', []):
                tags_set.add(tag)
        
        # Создать индекс
        index = {
            'app': app_name,
            'app_full_name': pages[0].get('app_full_name', app_name) if pages else app_name,
            'version': '1.0.0',
            'last_update': datetime.now().isoformat(),
            'total_pages': len(pages),
            'total_words': total_words,
            'categories': categories,
            'tags': sorted(list(tags_set)),
            'pages': pages
        }
        
        # Статистика
        logger.info(f"   Pages:      {index['total_pages']}")
        logger.info(f"   Words:      {index['total_words']:,}")
        logger.info(f"   Categories: {len(categories)}")
        logger.info(f"   Tags:       {len(tags_set)}")
        
        # Сохранить в файл если указан
        if output_file:
            output_path = Path(output_file)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(index, f, indent=2, ensure_ascii=False)
            
            logger.success(f"✅ Index saved: {output_path}")
        else:
            # Сохранить в директорию приложения
            index_path = app_dir / 'index.json'
            with open(index_path, 'w', encoding='utf-8') as f:
                json.dump(index, f, indent=2, ensure_ascii=False)
            
            logger.success(f"✅ Index saved: {index_path}")
        
        return index
    
    def build_global_index(self, output_file: str = "global_index.json") -> Dict:
        """
        Создать глобальный индекс всех приложений
        
        Args:
            output_file: Путь для сохранения
            
        Returns:
            Глобальный индекс
        """
        if not self.base_dir.exists():
            logger.error(f"Base directory not found: {self.base_dir}")
            return {}
        
        logger.info(f"📚 Building global index")
        
        # Найти все приложения
        app_dirs = [d for d in self.base_dir.iterdir() if d.is_dir()]
        logger.info(f"   Found: {len(app_dirs)} apps")
        
        apps = []
        total_pages = 0
        total_words = 0
        
        for app_dir in app_dirs:
            app_name = app_dir.name
            
            # Попробовать загрузить существующий индекс
            app_index_path = app_dir / 'index.json'
            
            if app_index_path.exists():
                with open(app_index_path, 'r', encoding='utf-8') as f:
                    app_index = json.load(f)
            else:
                # Построить индекс если не существует
                logger.info(f"   Building missing index for: {app_name}")
                app_index = self.build_app_index(app_name)
            
            # Добавить в список
            apps.append({
                'app': app_name,
                'app_full_name': app_index.get('app_full_name', app_name),
                'total_pages': app_index.get('total_pages', 0),
                'total_words': app_index.get('total_words', 0),
                'categories': app_index.get('categories', {}),
                'tags': app_index.get('tags', []),
                'last_update': app_index.get('last_update', '')
            })
            
            total_pages += app_index.get('total_pages', 0)
            total_words += app_index.get('total_words', 0)
        
        # Создать глобальный индекс
        global_index = {
            'version': '1.0.0',
            'generated': datetime.now().isoformat(),
            'total_apps': len(apps),
            'total_pages': total_pages,
            'total_words': total_words,
            'apps': apps
        }
        
        # Сохранить
        output_path = Path(output_file)
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(global_index, f, indent=2, ensure_ascii=False)
        
        logger.success(f"✅ Global index saved: {output_path}")
        logger.info(f"\n📊 Global Stats:")
        logger.info(f"   Apps:  {global_index['total_apps']}")
        logger.info(f"   Pages: {global_index['total_pages']}")
        logger.info(f"   Words: {global_index['total_words']:,}")
        
        return global_index
    
    def search_index(self, query: str, app_name: Optional[str] = None) -> List[Dict]:
        """
        Поиск по индексам
        
        Args:
            query: Поисковый запрос
            app_name: Фильтр по приложению (опционально)
            
        Returns:
            Список найденных страниц
        """
        query_lower = query.lower()
        results = []
        
        # Определить где искать
        if app_name:
            app_dirs = [self.base_dir / app_name]
        else:
            app_dirs = [d for d in self.base_dir.iterdir() if d.is_dir()]
        
        for app_dir in app_dirs:
            index_path = app_dir / 'index.json'
            
            if not index_path.exists():
                continue
            
            with open(index_path, 'r', encoding='utf-8') as f:
                index = json.load(f)
            
            # Поиск по страницам
            for page in index.get('pages', []):
                # Поиск в заголовке
                if query_lower in page.get('title', '').lower():
                    results.append(page)
                    continue
                
                # Поиск в тегах
                if any(query_lower in tag.lower() for tag in page.get('tags', [])):
                    results.append(page)
                    continue
                
                # Поиск в категории
                if query_lower in page.get('category', '').lower():
                    results.append(page)
        
        return results


def main():
    """Точка входа CLI"""
    parser = argparse.ArgumentParser(
        description="DocAgent Indexer - Build JSON indexes for documentation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Build index for specific app
  python build_index.py --app dbgpt
  
  # Build global index
  python build_index.py --all --output global_index.json
  
  # Search in indexes
  python build_index.py --search "RAG" --app dbgpt
        """
    )
    
    parser.add_argument(
        '--app',
        type=str,
        help='ID приложения для индексации'
    )
    
    parser.add_argument(
        '--all',
        action='store_true',
        help='Построить глобальный индекс всех приложений'
    )
    
    parser.add_argument(
        '--base-dir',
        type=str,
        default='knowledge_base',
        help='Базовая директория (по умолчанию: knowledge_base)'
    )
    
    parser.add_argument(
        '--output',
        type=str,
        help='Путь для сохранения индекса'
    )
    
    parser.add_argument(
        '--search',
        type=str,
        help='Поисковый запрос'
    )
    
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Подробный вывод'
    )
    
    args = parser.parse_args()
    
    try:
        # Создать indexer
        indexer = DocAgentIndexer(base_dir=args.base_dir)
        
        # Выполнить команду
        if args.search:
            results = indexer.search_index(args.search, app_name=args.app)
            
            logger.info(f"\n🔍 Search results for '{args.search}':")
            logger.info(f"   Found: {len(results)} pages\n")
            
            for i, page in enumerate(results, 1):
                logger.info(f"{i}. {page.get('title', 'Untitled')}")
                logger.info(f"   App: {page.get('app', 'unknown')}")
                logger.info(f"   URL: {page.get('source', 'N/A')}")
                logger.info("")
        
        elif args.all:
            output = args.output or 'global_index.json'
            indexer.build_global_index(output_file=output)
        
        elif args.app:
            indexer.build_app_index(args.app, output_file=args.output)
        
        else:
            parser.print_help()
            logger.warning("\nNo action specified. Use --app, --all, or --search")
    
    except KeyboardInterrupt:
        logger.warning("\n⚠️ Interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"❌ Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
