#!/usr/bin/env python3
"""
Тестовый скрипт для отладки парсинга OpenSPG на yuque.com
"""
import asyncio
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode

async def test_openspg():
    url = "https://openspg.yuque.com/ndx6g9/0.8.en"
    
    print(f"🕸️ Testing: {url}")
    print("=" * 60)
    
    # Конфигурация с ожиданием загрузки
    browser_config = BrowserConfig(
        headless=True,
        verbose=True
    )
    
    crawl_config = CrawlerRunConfig(
        cache_mode=CacheMode.BYPASS,
        delay_before_return_html=8.0,  # Просто ждем 8 секунд
        page_timeout=120000,  # 2 минуты timeout
        excluded_tags=['script', 'style', 'nav', 'footer'],
        remove_overlay_elements=True,
    )
    
    async with AsyncWebCrawler(config=browser_config) as crawler:
        result = await crawler.arun(url=url, config=crawl_config)
        
        if result.success:
            print(f"\n✅ Success!")
            print(f"📄 Title: {result.metadata.get('title', 'N/A')}")
            print(f"📝 Markdown length: {len(result.markdown)} characters")
            print(f"📝 HTML length: {len(result.html)} characters")
            print(f"🔗 Links found: {len(result.links.get('internal', []))} internal")
            
            # Показываем первые 500 символов markdown
            print(f"\n📄 First 500 chars of markdown:")
            print("-" * 60)
            print(result.markdown[:500])
            print("-" * 60)
            
            # Показываем первые 10 ссылок
            internal_links = result.links.get('internal', [])
            if internal_links:
                print(f"\n🔗 First 10 internal links:")
                for link in internal_links[:10]:
                    href = link.get('href', '')
                    text = link.get('text', '')
                    print(f"   - {href} | {text}")
            
            # Сохраняем для проверки
            with open("D:/docs/DocAgent/knowledge_base/test/openspg_test.md", "w", encoding="utf-8") as f:
                f.write(result.markdown)
            
            with open("D:/docs/DocAgent/knowledge_base/test/openspg_test.html", "w", encoding="utf-8") as f:
                f.write(result.html)
            
            print(f"\n💾 Saved to knowledge_base/test/openspg_test.*")
        else:
            print(f"❌ Failed: {result.error_message}")

if __name__ == "__main__":
    asyncio.run(test_openspg())
