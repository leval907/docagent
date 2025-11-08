#!/usr/bin/env python3
"""
DocAgent Postprocessor
Добавляет YAML front matter к собранным markdown файлам
"""

import os
import sys
import re
import yaml
import hashlib
import argparse
from pathlib import Path
from datetime import datetime
from typing import Dict, Optional, List
from loguru import logger

# Настройка логирования
logger.remove()
logger.add(sys.stderr, format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>")


class MetadataInjector:
    """Класс для добавления метаданных в markdown файлы"""
    
    def __init__(self, base_dir: str = "knowledge_base", config_path: str = "config/sources.yaml"):
        """
        Инициализация
        
        Args:
            base_dir: Базовая директория с markdown файлами
            config_path: Путь к конфигу источников
        """
        self.base_dir = Path(base_dir)
        self.config_path = Path(config_path)
        self.config = self._load_config()
        
        logger.info(f"MetadataInjector initialized")
        logger.info(f"Base dir: {self.base_dir.absolute()}")
    
    def _load_config(self) -> Dict:
        """Загрузить конфигурацию"""
        if self.config_path.exists():
            with open(self.config_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)
        return {}
    
    def extract_title(self, content: str) -> str:
        """
        Извлечь заголовок из markdown
        
        Args:
            content: Содержимое файла
            
        Returns:
            Заголовок или пустая строка
        """
        lines = content.split('\n')
        for line in lines:
            # Ищем первый H1 заголовок
            match = re.match(r'^#\s+(.+)$', line.strip())
            if match:
                return match.group(1).strip()
        return ""
    
    def extract_metadata_from_content(self, content: str) -> Dict:
        """
        Извлечь дополнительные метаданные из контента
        
        Args:
            content: Содержимое файла
            
        Returns:
            Словарь с метаданными
        """
        metadata = {
            'word_count': len(content.split()),
            'line_count': len(content.split('\n')),
            'has_code': '```' in content,
        }
        
        # Извлечь заголовки всех уровней
        headers = re.findall(r'^#{1,6}\s+(.+)$', content, re.MULTILINE)
        metadata['headers_count'] = len(headers)
        
        # Извлечь ссылки
        links = re.findall(r'\[([^\]]+)\]\(([^\)]+)\)', content)
        metadata['links_count'] = len(links)
        
        # Извлечь блоки кода
        code_blocks = re.findall(r'```(\w+)?\n(.*?)```', content, re.DOTALL)
        if code_blocks:
            languages = [lang for lang, _ in code_blocks if lang]
            metadata['code_languages'] = list(set(languages))
            metadata['code_blocks_count'] = len(code_blocks)
        
        return metadata
    
    def calculate_file_hash(self, file_path: Path) -> str:
        """
        Вычислить SHA256 хеш файла
        
        Args:
            file_path: Путь к файлу
            
        Returns:
            Хеш строка
        """
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()
    
    def has_yaml_frontmatter(self, content: str) -> bool:
        """
        Проверить есть ли уже YAML front matter
        
        Args:
            content: Содержимое файла
            
        Returns:
            True если есть
        """
        return content.startswith('---\n')
    
    def add_yaml_frontmatter(
        self,
        file_path: Path,
        app_name: str,
        source_url: Optional[str] = None,
        force: bool = False
    ) -> bool:
        """
        Добавить YAML front matter к файлу
        
        Args:
            file_path: Путь к markdown файлу
            app_name: Имя приложения
            source_url: URL источника
            force: Перезаписать существующий front matter
            
        Returns:
            True если успешно
        """
        if not file_path.exists():
            logger.error(f"File not found: {file_path}")
            return False
        
        # Прочитать файл
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Проверить есть ли уже front matter
        if self.has_yaml_frontmatter(content) and not force:
            logger.debug(f"Skipping (already has frontmatter): {file_path.name}")
            return False
        
        # Если есть frontmatter и force=True, удалить старый
        if self.has_yaml_frontmatter(content) and force:
            parts = content.split('---\n', 2)
            if len(parts) >= 3:
                content = parts[2]
        
        # Извлечь метаданные
        title = self.extract_title(content) or file_path.stem.replace('_', ' ').title()
        content_metadata = self.extract_metadata_from_content(content)
        file_hash = self.calculate_file_hash(file_path)
        
        # Получить конфиг приложения
        app_config = self.config.get('apps', {}).get(app_name, {})
        
        # Построить URL источника
        if not source_url and app_config:
            base_url = app_config.get('url', '')
            # Попробовать восстановить URL из имени файла
            if base_url:
                # Убрать последний сегмент пути из base_url
                base_url = base_url.rstrip('/')
                file_slug = file_path.stem.replace('_', '-')
                source_url = f"{base_url}/{file_slug}"
        
        # Создать метаданные
        metadata = {
            'title': title,
            'source': source_url or '',
            'app': app_name,
            'app_full_name': app_config.get('name', app_name),
            'category': app_config.get('category', ''),
            'tags': app_config.get('tags', []),
            'date_crawled': datetime.now().isoformat(),
            'last_updated': datetime.now().isoformat(),
            'file_path': str(file_path.relative_to(self.base_dir.parent)),
            'word_count': content_metadata['word_count'],
            'has_code': content_metadata['has_code'],
            'code_languages': content_metadata.get('code_languages', []),
            'headers_count': content_metadata['headers_count'],
            'links_count': content_metadata['links_count'],
            'file_hash': file_hash,
        }
        
        # Сформировать YAML
        yaml_str = yaml.dump(metadata, allow_unicode=True, sort_keys=False)
        
        # Собрать новый контент
        new_content = f"---\n{yaml_str}---\n\n{content}"
        
        # Записать обратно
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        
        logger.success(f"✅ Added metadata: {file_path.name}")
        return True
    
    def process_app_docs(self, app_name: str, force: bool = False) -> Dict[str, int]:
        """
        Обработать все документы приложения
        
        Args:
            app_name: Имя приложения
            force: Перезаписать существующие метаданные
            
        Returns:
            Статистика {processed, skipped, errors}
        """
        app_dir = self.base_dir / app_name
        
        if not app_dir.exists():
            logger.error(f"App directory not found: {app_dir}")
            return {'processed': 0, 'skipped': 0, 'errors': 0}
        
        logger.info(f"🔍 Processing app: {app_name}")
        logger.info(f"   Directory: {app_dir}")
        
        stats = {'processed': 0, 'skipped': 0, 'errors': 0}
        
        # Найти все markdown файлы
        md_files = list(app_dir.glob("*.md"))
        logger.info(f"   Found: {len(md_files)} markdown files")
        
        for md_file in md_files:
            try:
                success = self.add_yaml_frontmatter(md_file, app_name, force=force)
                if success:
                    stats['processed'] += 1
                else:
                    stats['skipped'] += 1
            except Exception as e:
                logger.error(f"❌ Error processing {md_file.name}: {e}")
                stats['errors'] += 1
        
        logger.info(f"\n📊 Stats for {app_name}:")
        logger.info(f"   Processed: {stats['processed']}")
        logger.info(f"   Skipped:   {stats['skipped']}")
        logger.info(f"   Errors:    {stats['errors']}")
        
        return stats
    
    def process_all_apps(self, force: bool = False) -> Dict[str, Dict[str, int]]:
        """
        Обработать все приложения
        
        Args:
            force: Перезаписать существующие метаданные
            
        Returns:
            Статистика по всем приложениям
        """
        if not self.base_dir.exists():
            logger.error(f"Base directory not found: {self.base_dir}")
            return {}
        
        # Найти все поддиректории (приложения)
        app_dirs = [d for d in self.base_dir.iterdir() if d.is_dir()]
        
        logger.info(f"📚 Processing {len(app_dirs)} apps")
        
        all_stats = {}
        for app_dir in app_dirs:
            app_name = app_dir.name
            logger.info(f"\n{'='*60}")
            stats = self.process_app_docs(app_name, force=force)
            all_stats[app_name] = stats
        
        # Общая статистика
        logger.info(f"\n{'='*60}")
        logger.info("📊 Total Summary:")
        
        total_processed = sum(s['processed'] for s in all_stats.values())
        total_skipped = sum(s['skipped'] for s in all_stats.values())
        total_errors = sum(s['errors'] for s in all_stats.values())
        
        logger.info(f"   Apps:      {len(all_stats)}")
        logger.info(f"   Processed: {total_processed}")
        logger.info(f"   Skipped:   {total_skipped}")
        logger.info(f"   Errors:    {total_errors}")
        
        return all_stats


def main():
    """Точка входа CLI"""
    parser = argparse.ArgumentParser(
        description="DocAgent Postprocessor - Add YAML front matter to markdown files",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Process specific app
  python postprocess.py --app dbgpt
  
  # Process all apps
  python postprocess.py --all
  
  # Force overwrite existing metadata
  python postprocess.py --app dbgpt --force
        """
    )
    
    parser.add_argument(
        '--app',
        type=str,
        help='ID приложения для обработки'
    )
    
    parser.add_argument(
        '--all',
        action='store_true',
        help='Обработать все приложения'
    )
    
    parser.add_argument(
        '--base-dir',
        type=str,
        default='knowledge_base',
        help='Базовая директория с markdown файлами (по умолчанию: knowledge_base)'
    )
    
    parser.add_argument(
        '--config',
        type=str,
        default='config/sources.yaml',
        help='Путь к файлу конфигурации (по умолчанию: config/sources.yaml)'
    )
    
    parser.add_argument(
        '--force',
        action='store_true',
        help='Перезаписать существующие метаданные'
    )
    
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Подробный вывод'
    )
    
    args = parser.parse_args()
    
    # Настроить логирование
    if args.verbose:
        logger.level("DEBUG")
    
    try:
        # Создать injector
        injector = MetadataInjector(base_dir=args.base_dir, config_path=args.config)
        
        # Выполнить команду
        if args.all:
            injector.process_all_apps(force=args.force)
        elif args.app:
            injector.process_app_docs(args.app, force=args.force)
        else:
            parser.print_help()
            logger.warning("\nNo action specified. Use --app or --all")
    
    except KeyboardInterrupt:
        logger.warning("\n⚠️ Interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"❌ Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
