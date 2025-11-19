# Crawl4AI Integration Guide

## Что такое Crawl4AI?

**Crawl4AI** - современный web-crawler с поддержкой JavaScript-рендеринга, оптимизированный для LLM и RAG систем.

### Преимущества

✅ **JavaScript-рендеринг** через Playwright  
✅ **SPA Support** (React, Vue, VitePress)  
✅ **Автоматическое извлечение** метаданных  
✅ **Markdown конвертация** из любого HTML  
✅ **Извлечение ссылок** для рекурсивного обхода  
✅ **Stealth mode** для обхода защиты  

### vs markdown-crawler

| Функция | Crawl4AI | markdown-crawler |
|---------|----------|------------------|
| JavaScript | ✅ | ❌ |
| SPA сайты | ✅ | ❌ |
| Скорость | 🐢 Медленнее | 🚀 Быстрее |
| Надёжность | ✅ Высокая | ⚠️ Средняя |
| Размер | 📦 ~400 MB | 📦 ~10 MB |

**Рекомендация**: Используйте Crawl4AI для современных сайтов документации.

## Установка

```bash
# Активировать venv
.venv\Scripts\Activate.ps1  # Windows
source .venv/bin/activate   # Linux/Mac

# Установить Crawl4AI
pip install crawl4ai

# Установить браузеры Playwright
playwright install
```

## Использование

### Базовый пример

```python
import asyncio
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig

async def crawl_page():
    browser_config = BrowserConfig(headless=True, verbose=True)
    crawl_config = CrawlerRunConfig(cache_mode=CacheMode.BYPASS)
    
    async with AsyncWebCrawler(config=browser_config) as crawler:
        result = await crawler.arun(
            url="https://nocodb.com/docs/product-docs",
            config=crawl_config
        )
        
        if result.success:
            print(f"Title: {result.metadata['title']}")
            print(f"Markdown: {result.markdown[:500]}...")
            print(f"Links: {len(result.links['internal'])} internal")

asyncio.run(crawl_page())
```

### Рекурсивный обход

```python
async def crawl_recursive(start_url, max_depth=3, max_pages=50):
    visited = set()
    to_visit = [(start_url, 0)]
    
    async with AsyncWebCrawler(config=browser_config) as crawler:
        while to_visit and len(visited) < max_pages:
            url, depth = to_visit.pop(0)
            
            if url in visited or depth > max_depth:
                continue
            
            visited.add(url)
            result = await crawler.arun(url=url)
            
            # Сохранить result.markdown
            # Добавить internal links в to_visit
```

## DocAgent Integration

### Скрипт crawler_crawl4ai.py

Полнофункциональный crawler с:
- Рекурсивным обходом
- Фильтрацией по домену
- Автоматическим сохранением
- YAML метаданными
- JSON индексацией

**Запуск**:
```bash
python scripts/crawler_crawl4ai.py --app nocodb
```

### Конфигурация

В `config/sources.yaml` добавить:
```yaml
apps:
  nocodb:
    name: "NocoDB"
    url: "https://nocodb.com/docs/product-docs"
    depth: 2           # Глубина рекурсии
    max_pages: 50      # Максимум страниц
    enabled: true
```

### Результаты

```
knowledge_base/nocodb/
├── docs-product-docs.md
├── docs-product-docs-bases.md
├── docs-product-docs-bases-create-base.md
├── ...
└── index.json
```

Каждый файл содержит:
```markdown
---
title: "Create Base"
source: "https://nocodb.com/docs/..."
crawled_at: "2025-11-09T00:26:31"
file_hash: "01768ce..."
word_count: 356
---

# Create base
...
```

## Тестирование

### NocoDB (протестировано ✅)

```bash
python scripts/crawler_crawl4ai.py --app nocodb
```

**Результат**:
- ✅ 50 страниц
- ✅ 26,988 слов
- ✅ ~2 минуты
- ✅ Все метаданные

### Другие сайты

**Работает**:
- ✅ FastAPI (https://fastapi.tiangolo.com/)
- ✅ Requesty AI (https://docs.requesty.ai/)
- ✅ LangChain (https://python.langchain.com/)

**Проблемы**:
- ⚠️ DB-GPT (SSL ошибки на некоторых хостах)

## Настройка производительности

### Скорость

```python
# Быстрее (без рендеринга)
crawl_config = CrawlerRunConfig(
    wait_for="none",
    css_selector=None
)

# Медленнее (полный рендеринг)
crawl_config = CrawlerRunConfig(
    wait_for="networkidle",
    delay_before_return_html=2.0
)
```

### Задержки

```python
# В crawler_crawl4ai.py:
await asyncio.sleep(0.5)  # 500ms между запросами
```

Можно уменьшить до 0.1-0.2 секунд, но риск блокировки.

### Параллелизм

**Не реализовано** (но возможно):
```python
# Создать несколько AsyncWebCrawler
# Распределить URLs между ними
# Собрать результаты
```

## Обработка ошибок

### Типичные проблемы

**1. SSL Errors**
```
SSLError: [SSL: UNEXPECTED_EOF_WHILE_READING]
```
**Решение**: Добавить `verify_ssl=False` в BrowserConfig

**2. Timeout**
```
TimeoutError: Page didn't load in time
```
**Решение**: Увеличить `page_timeout` в CrawlerRunConfig

**3. No links found**
```
DEBUG: Found 0 child URLs
```
**Проверить**: Правильность base_url и domain matching

### Логирование

```python
from loguru import logger

logger.add("logs/crawler.log", rotation="10 MB")
logger.info("Crawling {url}", url=url)
```

## Расширенные возможности

### Извлечение данных

```python
# Структурированные данные
result = await crawler.arun(
    url=url,
    extraction_strategy=JsonCssExtractionStrategy(
        schema={
            "title": "h1",
            "content": "article",
            "links": "a[href]"
        }
    )
)
```

### Скриншоты

```python
result = await crawler.arun(
    url=url,
    screenshot=True
)
# result.screenshot содержит base64
```

### Кастомные селекторы

```python
crawl_config = CrawlerRunConfig(
    css_selector="article.documentation",
    excluded_tags=['nav', 'footer', 'aside']
)
```

## Docker

```dockerfile
FROM python:3.11-slim

RUN pip install crawl4ai playwright
RUN playwright install chromium
RUN playwright install-deps

COPY . /app
WORKDIR /app

CMD ["python", "scripts/crawler_crawl4ai.py", "--app", "nocodb"]
```

## FAQ

**Q: Почему так медленно?**  
A: Playwright запускает реальный браузер. ~1-2 сек/страница это норма.

**Q: Можно ли ускорить?**  
A: Да, через параллелизм (несколько crawler'ов) или headless режим.

**Q: Работает ли с API документацией?**  
A: Да, если она отображается как HTML страницы.

**Q: Как обойти Cloudflare?**  
A: Используйте `stealth_mode=True` и добавьте задержки.

**Q: Нужен ли markdown-crawler?**  
A: Нет, Crawl4AI его заменяет полностью.

## Ссылки

- 📚 [Crawl4AI Docs](https://docs.crawl4ai.com)
- 🐙 [GitHub](https://github.com/unclecode/crawl4ai)
- 💬 [Discord](https://discord.gg/crawl4ai)

---

**Автор**: DocAgent Team  
**Дата**: 09.11.2025  
**Версия**: 2.0
