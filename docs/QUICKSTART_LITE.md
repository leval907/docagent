# 🚀 Quick Start - Lite Pipeline

**Быстрый старт для экспериментов с chunking + embedding + поиск**

## ✅ Что работает

```
✅ SQLite база данных (один файл)
✅ sentence-transformers (локальные embeddings без API)
✅ Chunking с настраиваемым размером и overlap
✅ Векторный поиск через cosine similarity
✅ Загрузка из markdown файлов
✅ Опциональный краулинг через Crawl4AI
```

## 🏁 Быстрый старт (3 минуты)

### 1. Установка

```bash
# Только эти две библиотеки нужны
pip install sentence-transformers crawl4ai
```

### 2. Загрузка документов

```bash
cd D:\docs\DocAgent

# Загрузить 5 документов OpenSPG
Get-ChildItem "knowledge_base\openspg\*.md" | Select-Object -First 5 | ForEach-Object {
    python scripts\pipeline_lite.py load $_.FullName --app openspg
}
```

**Результат:**
```
✅ База данных инициализирована: docagent_lite.db
📦 Загрузка модели all-MiniLM-L6-v2...
✅ Модель загружена, размерность: 384
📄 Документ разбит на 4 chunks
🧠 Embeddings сгенерированы: (4, 384)
✅ Документ сохранен: ID=5, chunks=4
```

### 3. Поиск

```bash
# Поиск по всем документам
python scripts\pipeline_lite.py search "OpenSPG"

# Поиск только в OpenSPG
python scripts\pipeline_lite.py search "knowledge graph" --app openspg --limit 5
```

**Результат:**
```
🔍 Найдено результатов: 5

1. [Document Title] (0.847)
   URL: file://D:\docs\DocAgent\knowledge_base\openspg\doc1.md
   App: openspg
   Текст: OpenSPG is a knowledge graph engine that allows you to...

2. [Another Document] (0.782)
   ...
```

### 4. Статистика

```bash
python scripts\pipeline_lite.py stats
```

**Результат:**
```
📊 Статистика
Документов: 5
Chunks: 10

По приложениям:
  openspg: 5 docs, 3091 words, 9 chunks
```

## 📖 Полная команда

```bash
# Помощь
python scripts\pipeline_lite.py --help

# Загрузка файла
python scripts\pipeline_lite.py load <file.md> --app <app_id> --title "Title"

# Краулинг URL
python scripts\pipeline_lite.py crawl <url> --app <app_id>

# Поиск
python scripts\pipeline_lite.py search "<query>" --app <app_id> --limit 10

# Статистика
python scripts\pipeline_lite.py stats

# Другая база
python scripts\pipeline_lite.py --db mydb.db stats

# Другая модель
python scripts\pipeline_lite.py --model all-mpnet-base-v2 load file.md
```

## 🧪 Тестовые сценарии

### Сценарий 1: Загрузка всех OpenSPG

```powershell
cd D:\docs\DocAgent

Get-ChildItem "knowledge_base\openspg\*.md" | ForEach-Object {
    python scripts\pipeline_lite.py load $_.FullName --app openspg
}

python scripts\pipeline_lite.py stats
python scripts\pipeline_lite.py search "schema definition" --app openspg
```

### Сценарий 2: Эксперименты с chunk size

```python
# test_chunks.py
from scripts.pipeline_lite import DocumentPipelineLite

# Тест 1: Маленькие chunks
p1 = DocumentPipelineLite(db_path="test_small.db", chunk_size=300, chunk_overlap=30)
p1.load_from_file("knowledge_base/openspg/0.8.en.md", app_id="test1")
results1 = p1.search("OpenSPG", app_id="test1")
print(f"Small chunks: {len(results1)} results")

# Тест 2: Большие chunks
p2 = DocumentPipelineLite(db_path="test_large.db", chunk_size=1000, chunk_overlap=100)
p2.load_from_file("knowledge_base/openspg/0.8.en.md", app_id="test2")
results2 = p2.search("OpenSPG", app_id="test2")
print(f"Large chunks: {len(results2)} results")
```

### Сценарий 3: Программное использование

```python
from scripts.pipeline_lite import DocumentPipelineLite

# Инициализация
pipeline = DocumentPipelineLite(
    db_path="my_docs.db",
    model_name="all-MiniLM-L6-v2",
    chunk_size=500,
    chunk_overlap=50
)

# Загрузка документов
pipeline.load_from_file(
    file_path="docs/article.md",
    title="My Article",
    app_id="blog"
)

# Поиск
results = pipeline.search(
    query="machine learning",
    app_id="blog",
    limit=10,
    min_similarity=0.5
)

for result in results:
    print(f"{result['title']}: {result['similarity']:.3f}")
    print(result['chunk_text'][:200])
```

## 🔧 Настройки

### Размер chunks

```python
# Короткие chunks - лучше точность
pipeline = DocumentPipelineLite(chunk_size=300, chunk_overlap=30)

# Длинные chunks - больше контекста
pipeline = DocumentPipelineLite(chunk_size=1000, chunk_overlap=100)
```

### Модель embeddings

```bash
# Легкая (по умолчанию)
--model all-MiniLM-L6-v2  # 80MB, 384 dim

# Точная
--model all-mpnet-base-v2  # 420MB, 768 dim

# Многоязычная
--model paraphrase-multilingual-MiniLM-L12-v2  # 470MB, 384 dim
```

### Минимальный similarity

```python
# Строгий поиск
results = pipeline.search(query, min_similarity=0.7)

# Мягкий поиск
results = pipeline.search(query, min_similarity=0.3)
```

## 📊 Что внутри docagent_lite.db

```sql
-- Просмотр документов
sqlite3 docagent_lite.db "SELECT id, title, app_id, chunk_count FROM documents;"

-- Просмотр chunks
sqlite3 docagent_lite.db "SELECT document_id, chunk_index, word_count FROM chunks;"

-- Статистика
sqlite3 docagent_lite.db "
SELECT 
    app_id,
    COUNT(*) as docs,
    SUM(word_count) as total_words,
    SUM(chunk_count) as total_chunks
FROM documents
GROUP BY app_id;
"
```

## ⚡ Производительность

**На Intel i5, 16GB RAM, без GPU:**

| Операция | Время |
|----------|-------|
| Загрузка модели (первый раз) | ~3 сек |
| Chunking 5000 слов | ~0.1 сек |
| Embeddings 10 chunks | ~0.3 сек |
| Сохранение в SQLite | ~0.05 сек |
| Поиск по 100 chunks | ~1 сек |
| **Итого на документ** | **~4 сек** |

## 🎯 Следующие шаги

1. **Загрузить больше документов** для лучшего поиска
2. **Экспериментировать с chunk_size** и моделями
3. **Интегрировать в свое приложение** через Python API
4. **Добавить FAISS индекс** для быстрого поиска (>1000 chunks)
5. **Мигрировать на PostgreSQL+pgvector** для production

## 📚 Документация

- **[LITE_PIPELINE.md](./LITE_PIPELINE.md)** - Полное руководство
- **[scripts/pipeline_lite.py](./scripts/pipeline_lite.py)** - Исходный код

## ❓ FAQ

**Q: Почему similarity такой низкий (0.3-0.4)?**  
A: Короткие документы или много metadata. Попробуйте загрузить документы с большим количеством текста.

**Q: Как ускорить поиск?**  
A: Используйте фильтрацию по `app_id` или добавьте FAISS индекс.

**Q: Можно ли использовать OpenAI embeddings?**  
A: Да, замените `model.encode()` на `openai.Embedding.create()`.

**Q: Как мигрировать на production?**  
A: Экспортируйте данные из SQLite в PostgreSQL + используйте полный стек (см. COMPLETE_STACK.md).

---

**✨ Готово! За 3 минуты у вас полноценный векторный поиск по документам.**
