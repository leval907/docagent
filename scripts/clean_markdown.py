#!/usr/bin/env python3
"""
CleanMarkdown - Post-processing for cleaning crawled markdown
Удаляет мусор, навигацию, служебные элементы, нормализует форматирование
"""
import re
import os
from pathlib import Path
from typing import List, Dict
import yaml
from loguru import logger
import click


class MarkdownCleaner:
    """Очистка markdown файлов от мусора"""
    
    # Паттерны для удаления
    REMOVAL_PATTERNS = [
        # Навигационные элементы Yuque
        r'搜索⌘ \+ [JK]',
        r'首页\n目录',
        r'大纲',
        r'划词评论.*?',
        r'Press space bar to start a drag\..*',
        
        # Кнопки и ссылки на аккаунты
        r'\[免费使用\].*?\)',
        r'\[Try it free\].*?\)',
        r'\[关于语雀\].*?\[快速注册\].*?\)',
        r'若有收获，就点个赞吧',
        r'注册 / 登录.*?进行评论',
        
        # IP и служебная информация
        r'IP 属地.*?\n',
        r'举报\n?',
        r'\d+字\n',
        
        # Профили авторов (в конце документа)
        r'\[[\u4e00-\u9fa5]+\]\(https://.*?yuque\.com/.*?\)',  # Китайские имена со ссылками
        r'、\[[\u4e00-\u9fa5]+\]\(https://.*?yuque\.com/.*?\)',  # Separator + имя
        r'\d{2}-\d{2} \d{2}:\d{2}',  # Даты вида 06-24 11:59
        r'^\d+$',  # Одинокие цифры (счетчики просмотров)
        
        # Пустые ссылки и плейсхолдеры
        r'\[!\[\]\(.*?\)\]\(.*?\)',  # Вложенные картинки-ссылки
        r'!\[\]\(.*?\)',  # Пустые изображения
        
        # Повторяющиеся переводы строк
        r'\n{3,}',  # 3+ переноса -> 2
        
        # Артефакты HTML
        r'&amp;',
        r'&lt;',
        r'&gt;',
        r'&nbsp;',
        
        # Yuque специфичные элементы
        r'Adblocker',
        r'返回文档',
        r'Back to document',
        
        # Пустые символы и мусор
        r'​',  # Zero-width space
    ]
    
    # Паттерны замены
    REPLACEMENT_PATTERNS = {
        r'&amp;': '&',
        r'&lt;': '<',
        r'&gt;': '>',
        r'&nbsp;': ' ',
        r'\n{3,}': '\n\n',  # Множественные переносы -> двойной
        r'  +': ' ',  # Множественные пробелы -> одинарный
    }
    
    # Секции для удаления (от начала паттерна до конца файла)
    FOOTER_PATTERNS = [
        r'^首页\n',
        r'^目录\n',
        r'^大纲\n',
        r'^\[关于语雀\]',
    ]
    
    def __init__(self):
        logger.info("MarkdownCleaner initialized")
    
    def clean_text(self, text: str) -> str:
        """Основная очистка текста"""
        
        # 1. Удаляем футеры (всё после определенных паттернов)
        for pattern in self.FOOTER_PATTERNS:
            parts = re.split(pattern, text, flags=re.MULTILINE)
            if len(parts) > 1:
                text = parts[0]
        
        # 2. Удаляем паттерны
        for pattern in self.REMOVAL_PATTERNS:
            text = re.sub(pattern, '', text, flags=re.MULTILINE)
        
        # 3. Замены
        for pattern, replacement in self.REPLACEMENT_PATTERNS.items():
            text = re.sub(pattern, replacement, text)
        
        # 4. Очистка пустых строк в начале/конце
        text = text.strip()
        
        # 5. Нормализация переносов строк
        text = re.sub(r'\n{3,}', '\n\n', text)
        
        return text
    
    def extract_main_content(self, text: str) -> str:
        """Извлечь только основной контент (между заголовком и футером)"""
        
        # Ищем первый заголовок уровня 1
        match = re.search(r'^# (.+)$', text, re.MULTILINE)
        if match:
            # Берем всё после первого заголовка
            start_pos = match.start()
            
            # Ищем начало футера/навигации
            footer_patterns = [
                r'\n首页\n',
                r'\n目录\n',
                r'\n\[关于语雀\]',
                r'\n注册 / 登录',
            ]
            
            end_pos = len(text)
            for pattern in footer_patterns:
                footer_match = re.search(pattern, text[start_pos:])
                if footer_match:
                    potential_end = start_pos + footer_match.start()
                    end_pos = min(end_pos, potential_end)
            
            text = text[start_pos:end_pos]
        
        return text
    
    def clean_markdown_file(self, file_path: Path) -> bool:
        """Очистить markdown файл"""
        
        try:
            # Читаем файл
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Разделяем на YAML front matter и контент
            if content.startswith('---\n'):
                parts = content.split('---\n', 2)
                if len(parts) >= 3:
                    yaml_content = parts[1]
                    markdown_content = parts[2]
                else:
                    yaml_content = ""
                    markdown_content = content
            else:
                yaml_content = ""
                markdown_content = content
            
            # Сохраняем оригинальный размер
            original_size = len(markdown_content)
            
            # Очищаем
            cleaned_content = self.extract_main_content(markdown_content)
            cleaned_content = self.clean_text(cleaned_content)
            
            # Проверяем, что контент не стал слишком коротким
            if len(cleaned_content) < 100:
                logger.warning(f"Content too short after cleaning: {file_path.name}")
                return False
            
            # Обновляем word_count в YAML
            if yaml_content:
                try:
                    yaml_data = yaml.safe_load(yaml_content)
                    word_count = len(cleaned_content.split())
                    yaml_data['word_count'] = word_count
                    yaml_data['cleaned'] = True
                    yaml_content = yaml.dump(yaml_data, allow_unicode=True)
                except:
                    pass
            
            # Собираем обратно
            if yaml_content:
                final_content = f"---\n{yaml_content}---\n\n{cleaned_content}"
            else:
                final_content = cleaned_content
            
            # Сохраняем
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(final_content)
            
            reduction = ((original_size - len(cleaned_content)) / original_size) * 100
            logger.success(f"Cleaned {file_path.name}: {original_size} -> {len(cleaned_content)} chars ({reduction:.1f}% reduction)")
            
            return True
            
        except Exception as e:
            logger.error(f"Error cleaning {file_path}: {e}")
            return False
    
    def clean_directory(self, directory: Path, pattern: str = "*.md") -> Dict[str, int]:
        """Очистить все markdown файлы в директории"""
        
        stats = {
            'processed': 0,
            'cleaned': 0,
            'errors': 0,
            'skipped': 0
        }
        
        md_files = list(directory.glob(pattern))
        logger.info(f"Found {len(md_files)} markdown files in {directory}")
        
        for md_file in md_files:
            # Пропускаем index.json и другие не-markdown
            if md_file.suffix != '.md':
                continue
            
            stats['processed'] += 1
            
            if self.clean_markdown_file(md_file):
                stats['cleaned'] += 1
            else:
                stats['errors'] += 1
        
        return stats


@click.command()
@click.option('--app', required=True, help='App ID (e.g., openspg, nocodb)')
@click.option('--base-dir', default='knowledge_base', help='Base directory for markdown files')
@click.option('--dry-run', is_flag=True, help='Dry run without actual cleaning')
def main(app: str, base_dir: str, dry_run: bool):
    """Clean markdown files from crawled documentation"""
    
    logger.info("🧹 MarkdownCleaner starting")
    logger.info(f"   App: {app}")
    logger.info(f"   Base dir: {base_dir}")
    
    if dry_run:
        logger.warning("   DRY RUN MODE - no files will be modified")
    
    app_dir = Path(base_dir) / app
    
    if not app_dir.exists():
        logger.error(f"Directory not found: {app_dir}")
        return
    
    cleaner = MarkdownCleaner()
    
    if dry_run:
        # В dry run просто показываем что будет сделано
        md_files = list(app_dir.glob("*.md"))
        logger.info(f"Would clean {len(md_files)} files")
        for f in md_files[:5]:
            logger.info(f"   - {f.name}")
        if len(md_files) > 5:
            logger.info(f"   ... and {len(md_files) - 5} more")
    else:
        stats = cleaner.clean_directory(app_dir)
        
        logger.info("\n" + "="*60)
        logger.info("📊 Cleaning Statistics")
        logger.info("="*60)
        logger.success(f"   Processed: {stats['processed']}")
        logger.success(f"   Cleaned:   {stats['cleaned']}")
        if stats['errors'] > 0:
            logger.error(f"   Errors:    {stats['errors']}")
        if stats['skipped'] > 0:
            logger.warning(f"   Skipped:   {stats['skipped']}")


if __name__ == "__main__":
    main()
