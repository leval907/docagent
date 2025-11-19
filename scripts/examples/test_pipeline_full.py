#!/usr/bin/env python3
"""
Test Full Pipeline: Crawl → Docling → S3 → PostgreSQL → Analytics
"""

import sys
import asyncio
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig
from config.s3_config import upload_to_s3, list_s3_files
from datetime import datetime
import hashlib
import json


async def crawl_single_page(url: str, app_name: str) -> dict:
    """Crawl single page and save to S3"""
    
    config = BrowserConfig(headless=True, verbose=False)
    run_config = CrawlerRunConfig(excluded_tags=['script', 'style', 'nav', 'footer'])
    
    crawler = AsyncWebCrawler(config=config)
    
    try:
        await crawler.__aenter__()
        print(f"\n📄 Crawling: {url}")
        
        result = await crawler.arun(url=url, config=run_config)
        
        if not result.success:
            print(f"❌ Failed: {result.error_message}")
            return None
        
        print(f"✅ Crawled successfully")
        print(f"   Title: {result.metadata.get('title', 'N/A')}")
        print(f"   Markdown: {len(result.markdown)} chars")
        print(f"   Links: {len(result.links.get('internal', []))}")
        
        # Generate filename from URL
        url_hash = hashlib.md5(url.encode()).hexdigest()[:8]
        title_slug = result.metadata.get('title', 'page').lower().replace(' ', '-')[:50]
        filename = f"{title_slug}-{url_hash}"
        
        # Save markdown to temp file
        md_path = f"/tmp/{filename}.md"
        with open(md_path, 'w', encoding='utf-8') as f:
            f.write(result.markdown)
        
        # Upload to S3
        print(f"\n☁️  Uploading to S3...")
        s3_path = f"crawled/{app_name}/{filename}.md"
        upload_to_s3(md_path, s3_path)
        print(f"   ✅ {s3_path}")
        
        # Create metadata
        metadata = {
            "url": url,
            "title": result.metadata.get('title', 'N/A'),
            "app_name": app_name,
            "s3_path": s3_path,
            "word_count": len(result.markdown.split()),
            "char_count": len(result.markdown),
            "internal_links": len(result.links.get('internal', [])),
            "crawled_at": datetime.now().isoformat(),
            "file_hash": hashlib.md5(result.markdown.encode()).hexdigest()
        }
        
        # Save metadata
        meta_path = f"/tmp/{filename}.json"
        with open(meta_path, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)
        
        s3_meta_path = f"metadata/crawled/{app_name}/{filename}.json"
        upload_to_s3(meta_path, s3_meta_path)
        print(f"   ✅ {s3_meta_path}")
        
        return metadata
        
    finally:
        await crawler.__aexit__(None, None, None)


async def test_pipeline():
    """Test full pipeline with single DuckDB page"""
    
    # Test URLs
    test_cases = [
        {
            "url": "https://duckdb.org/docs/stable/",
            "app_name": "duckdb"
        },
        {
            "url": "https://duckdb.org/docs/stable/sql/introduction",
            "app_name": "duckdb"
        }
    ]
    
    results = []
    
    for test in test_cases:
        result = await crawl_single_page(test["url"], test["app_name"])
        if result:
            results.append(result)
    
    # Summary
    print(f"\n\n{'='*60}")
    print(f"📊 PIPELINE TEST SUMMARY")
    print(f"{'='*60}")
    print(f"Total pages crawled: {len(results)}")
    
    for r in results:
        print(f"\n📄 {r['title'][:60]}")
        print(f"   URL: {r['url']}")
        print(f"   S3: {r['s3_path']}")
        print(f"   Words: {r['word_count']}")
        print(f"   Links: {r['internal_links']}")
    
    # List all files in S3
    print(f"\n\n📁 Files in S3 (crawled/duckdb/):")
    files = list_s3_files("crawled/duckdb/")
    for f in files:
        print(f"   - {f}")
    
    print(f"\n✅ Pipeline test completed!")
    print(f"\n💡 Next steps:")
    print(f"   1. Index these pages in PostgreSQL with pgvector")
    print(f"   2. Create embeddings for semantic search")
    print(f"   3. Build knowledge graph in ArangoDB")
    print(f"   4. Track analytics in separate DuckDB database")


if __name__ == "__main__":
    asyncio.run(test_pipeline())
