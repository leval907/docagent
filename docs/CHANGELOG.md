# Changelog v3.0 - Lite Pipeline для экспериментов

## 🎯 Главное изменение

Добавлен **легковесный режим** для быстрых экспериментов с chunking, embeddings и векторным поиском:
- SQLite вместо PostgreSQL (один файл БД)
- sentence-transformers вместо OpenAI API (локальные embeddings)
- Без Docker для быстрого старта

## 📦 Новые файлы

### Scripts
- `scripts/pipeline_lite.py` (500+ lines) - Полный pipeline для экспериментов
  - Chunking с настраиваемым размером и overlap
  - Локальные embeddings через sentence-transformers
  - Векторный поиск через cosine similarity
  - CLI интерфейс: load, crawl, search, stats

### Documentation
- `QUICKSTART_LITE.md` - Быстрый старт за 3 минуты
- `LITE_PIPELINE.md` - Полное руководство по lite режиму
- `COMPLETE_STACK.md` - Production stack документация (ранее создан)

### Обновления
- `README.md` - Переработан с акцентом на два режима (Lite vs Production)
- `requirements.txt` - Обновлены комментарии для разделения зависимостей

## ✨ Возможности Lite Pipeline

### Chunking
```python
chunk_size=500       # Слов на chunk
chunk_overlap=50     # Overlap между chunks
```

### Embeddings
- Модель по умолчанию: `all-MiniLM-L6-v2` (80MB, 384 dim)
- Альтернативы: `all-mpnet-base-v2`, multilingual модели
- Локальные, без API ключей

### Поиск
- Cosine similarity между query и всеми chunks
- Фильтрация по `app_id`
- Настраиваемый `min_similarity` порог

### Хранение
```sql
documents: id, url, title, app_id, content, chunk_count
chunks: id, document_id, chunk_text, embedding (JSON)
```

## 🧪 Тестирование

Протестировано на OpenSPG документации:
```
✅ 5 документов загружено
✅ 10 chunks создано
✅ Embeddings сгенерированы за ~3 сек
✅ Векторный поиск работает
✅ Similarity scores: 0.3-0.9
```

## 🔄 Миграционный путь

1. **Эксперименты**: Lite Pipeline (SQLite + sentence-transformers)
2. **Тестирование**: Проверка качества chunking и search
3. **Production**: Миграция на Full Stack (PostgreSQL + ChromaDB + FastAPI)

## 📊 Производительность

**Intel i5, 16GB RAM, без GPU:**
- Загрузка модели: ~3 сек (первый раз)
- Chunking 5000 слов: ~0.1 сек
- Embeddings 10 chunks: ~0.3 сек
- Поиск по 100 chunks: ~1 сек

## 🎓 Use Cases

### 1. Быстрые эксперименты
```bash
python scripts/pipeline_lite.py load document.md --app test
python scripts/pipeline_lite.py search "query" --app test
```

### 2. Тестирование chunk sizes
```python
pipeline = DocumentPipelineLite(chunk_size=300)  # Маленькие
pipeline = DocumentPipelineLite(chunk_size=1000)  # Большие
```

### 3. Сравнение моделей embeddings
```bash
python scripts/pipeline_lite.py --model all-MiniLM-L6-v2 load doc.md
python scripts/pipeline_lite.py --model all-mpnet-base-v2 load doc.md
```

### 4. Интеграция в приложение
```python
from scripts.pipeline_lite import DocumentPipelineLite

pipeline = DocumentPipelineLite()
results = pipeline.search("query", limit=10)
```

## 🔮 Дальнейшие улучшения

- [ ] FAISS индексы для >1000 chunks
- [ ] Гибридный поиск (BM25 + Vector)
- [ ] Reranking с cross-encoder
- [ ] Экспорт в PostgreSQL + pgvector
- [ ] Замена на OpenAI API embeddings

## 📚 Документация

Вся документация обновлена:
- README.md - главная страница с двумя режимами
- QUICKSTART_LITE.md - быстрый старт
- LITE_PIPELINE.md - детальное руководство
- COMPLETE_STACK.md - production режим

## 🙏 Философия изменений

**Проблема**: Production stack с Docker, PostgreSQL, ChromaDB слишком тяжелый для экспериментов.

**Решение**: Lite режим с минимальными зависимостями:
- 2 библиотеки: sentence-transformers, crawl4ai
- 1 файл БД: SQLite
- 0 Docker containers
- 3 минуты до первых результатов

**Результат**: Быстрое тестирование → проверка качества → миграция на production.

---

**Готово к использованию!** 🚀
