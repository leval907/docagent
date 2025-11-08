#!/usr/bin/env python3
"""
Тестовый скрипт для проверки Crawl4AI
"""
import asyncio
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode

async def test_crawl():
    # Конфигурация браузера
    browser_config = BrowserConfig(
        headless=True,
        verbose=True
    )
    
    # Конфигурация краулера
    crawl_config = CrawlerRunConfig(
        cache_mode=CacheMode.BYPASS,
        markdown_generator=None,  # Используем дефолтный
    )
    
    # URL для тестирования
    url = "https://nocodb.com/docs/product-docs"
    
    print(f"🕸️ Crawling: {url}")
    
    async with AsyncWebCrawler(config=browser_config) as crawler:
        result = await crawler.arun(
            url=url,
            config=crawl_config
        )
        
        if result.success:
            print(f"✅ Success!")
            print(f"📄 Title: {result.metadata.get('title', 'N/A')}")
            print(f"📝 Markdown length: {len(result.markdown)} characters")
            print(f"🔗 Links found: {len(result.links.get('internal', []))} internal, {len(result.links.get('external', []))} external")
            
            # Сохраняем результат
            output_file = "D:/docs/DocAgent/knowledge_base/test/nocodb_test.md"
            import os
            os.makedirs(os.path.dirname(output_file), exist_ok=True)
            
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(f"# {result.metadata.get('title', 'Document')}\n\n")
                f.write(f"Source: {url}\n\n")
                f.write(result.markdown)
            
            print(f"💾 Saved to: {output_file}")
            
            # Показываем найденные внутренние ссылки
            internal_links = result.links.get('internal', [])
            if internal_links:
                print(f"\n🔗 First 10 internal links:")
                for link in internal_links[:10]:
                    print(f"   - {link}")
        else:
            print(f"❌ Failed: {result.error_message}")

if __name__ == "__main__":
    asyncio.run(test_crawl())
