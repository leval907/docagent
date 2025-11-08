#!/usr/bin/env python3
"""
Тестовый скрипт для проверки работы DocAgent парсера (Crawl4AI)
"""

import sys
import subprocess
from pathlib import Path
from loguru import logger

# Настройка логирования
logger.remove()
logger.add(sys.stderr, format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>")


def run_command(cmd: list, description: str):
    """Запустить команду"""
    logger.info(f"\n{'='*60}")
    logger.info(f"🚀 {description}")
    logger.info(f"{'='*60}")
    logger.info(f"Command: {' '.join(cmd)}\n")
    
    try:
        result = subprocess.run(
            cmd,
            check=True,
            capture_output=False,
            text=True
        )
        logger.success(f"✅ {description} - SUCCESS\n")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"❌ {description} - FAILED")
        logger.error(f"Error: {e}\n")
        return False
    except Exception as e:
        logger.error(f"❌ Unexpected error: {e}\n")
        return False


def check_crawl4ai():
    """Проверить наличие Crawl4AI"""
    try:
        import crawl4ai
        logger.success(f"✅ Crawl4AI {crawl4ai.__version__} found")
        return True
    except ImportError:
        logger.warning("⚠️ Crawl4AI not found!")
        logger.info("\nPlease install it:")
        logger.info("  pip install crawl4ai")
        logger.info("  playwright install")
        return False


def test_crawler():
    """Тест Crawl4AI crawler"""
    logger.info("\n" + "="*60)
    logger.info("📋 TEST 1: Crawl4AI Crawler")
    logger.info("="*60)
    
    # Тест с nocodb
    logger.info("\n1️⃣ Crawl NocoDB documentation:")
    run_command(
        [sys.executable, "scripts/crawler_crawl4ai.py", "--app", "nocodb"],
        "Crawl nocodb"
    )


def test_postprocessor():
    """Тест postprocessor"""
    logger.info("\n" + "="*60)
    logger.info("📋 TEST 2: Postprocessor")
    logger.info("="*60)
    
    # Проверить есть ли файлы для обработки
    kb_dir = Path("knowledge_base/nocodb")
    
    if not kb_dir.exists() or not list(kb_dir.glob("*.md")):
        logger.warning("⚠️ No markdown files found for testing")
        logger.info("Run crawler first:")
        logger.info("  python scripts/crawler_crawl4ai.py --app nocodb")
        return False
    
    # Запустить postprocessor
    run_command(
        [sys.executable, "scripts/postprocess.py", "--app", "nocodb"],
        "Add YAML metadata"
    )
    
    # Проверить результат
    md_files = list(kb_dir.glob("*.md"))
    if md_files:
        test_file = md_files[0]
        logger.info(f"\n📄 Sample file: {test_file.name}")
        
        with open(test_file, 'r', encoding='utf-8') as f:
            first_lines = ''.join(f.readlines()[:20])
        
        logger.info("First 20 lines:")
        logger.info("-" * 60)
        print(first_lines)
        logger.info("-" * 60)
    
    return True


def test_indexer():
    """Тест indexer"""
    logger.info("\n" + "="*60)
    logger.info("📋 TEST 3: Indexer")
    logger.info("="*60)
    
    # Построить индекс
    run_command(
        [sys.executable, "scripts/build_index.py", "--app", "nocodb"],
        "Build app index"
    )
    
    # Построить глобальный индекс
    run_command(
        [sys.executable, "scripts/build_index.py", "--all"],
        "Build global index"
    )
    
    return True


def full_pipeline_test():
    """Полный тест пайплайна"""
    logger.info("\n" + "="*60)
    logger.info("🚀 FULL PIPELINE TEST")
    logger.info("="*60)
    
    steps = [
        ("Crawler", [sys.executable, "scripts/crawler_crawl4ai.py", "--app", "nocodb"]),
        ("Postprocessor", [sys.executable, "scripts/postprocess.py", "--app", "nocodb"]),
        ("Indexer", [sys.executable, "scripts/build_index.py", "--app", "nocodb"]),
    ]
    
    results = []
    for step_name, cmd in steps:
        success = run_command(cmd, f"Step: {step_name}")
        results.append((step_name, success))
    
    # Итоговый отчёт
    logger.info("\n" + "="*60)
    logger.info("📊 PIPELINE TEST RESULTS")
    logger.info("="*60)
    
    for step_name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        logger.info(f"{status} - {step_name}")
    
    total_success = all(s for _, s in results)
    
    if total_success:
        logger.success("\n🎉 All tests passed!")
    else:
        logger.error("\n❌ Some tests failed")
    
    return total_success


def main():
    """Точка входа"""
    logger.info("🧪 DocAgent Test Suite (Crawl4AI)")
    logger.info("="*60)
    
    # Проверить Crawl4AI
    if not check_crawl4ai():
        logger.error("\n❌ Setup incomplete. Please install Crawl4AI first.")
        logger.info("  pip install crawl4ai")
        logger.info("  playwright install")
        return
    
    # Меню выбора
    logger.info("\nSelect test mode:")
    logger.info("  1 - Test crawler only")
    logger.info("  2 - Test postprocessor only")
    logger.info("  3 - Test indexer only")
    logger.info("  4 - Full pipeline test (recommended)")
    logger.info("  q - Quit")
    
    choice = input("\nEnter your choice [1-4, q]: ").strip()
    
    if choice == '1':
        test_crawler()
    elif choice == '2':
        test_postprocessor()
    elif choice == '3':
        test_indexer()
    elif choice == '4':
        full_pipeline_test()
    elif choice.lower() == 'q':
        logger.info("Bye! 👋")
    else:
        logger.warning("Invalid choice")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.warning("\n⚠️ Interrupted by user")
    except Exception as e:
        logger.error(f"❌ Fatal error: {e}")
