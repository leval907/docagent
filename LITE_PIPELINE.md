# 🧪 Легковесный пайплайн для экспериментов

**SQLite + sentence-transformers** - простой способ протестировать chunking, embeddings и векторный поиск локально.

## 🎯 Что это?

Упрощенная версия для **быстрых экспериментов** на компьютере:
- ✅ **Без Docker** - просто Python
- ✅ **SQLite** - встроенная БД, один файл
- ✅ **sentence-transformers** - локальные embeddings без API
- ✅ **Легковесно** - модель ~80MB, быстрый старт

## 🚀 Быстрый старт

### 1. Установка зависимостей

```bash
pip install sentence-transformers crawl4ai
```

### 2. Загрузка существующих файлов

```bash
# Загрузить markdown файл
python scripts/pipeline_lite.py load knowledge_base/openspg/intro.md --app openspg --title "OpenSPG Introduction"

# Загрузить все файлы из папки
for file in knowledge_base/openspg/*.md; do
    python scripts/pipeline_lite.py load "$file" --app openspg
done
```

### 3. Поиск

```bash
# Поиск по всем документам
python scripts/pipeline_lite.py search "knowledge graph"

# Поиск только в OpenSPG
python scripts/pipeline_lite.py search "schema definition" --app openspg --limit 10
```

### 4. Статистика

```bash
python scripts/pipeline_lite.py stats
```

### 5. Краулинг (опционально)

```bash
python scripts/pipeline_lite.py crawl "https://openspg.yuque.com/ndx6g9/manual/intro" --app openspg
```

## 📊 Что происходит внутри?

### 1. Chunking
```
Документ (5000 слов)
    ↓
Chunk 1 (500 слов)
Chunk 2 (500 слов, overlap 50)
Chunk 3 (500 слов, overlap 50)
...
Chunk 10 (500 слов)
```

**Параметры:**
- `chunk_size=500` - слов на chunk
- `chunk_overlap=50` - слов overlap между chunks

### 2. Embeddings

Модель: `all-MiniLM-L6-v2`
- Размер: ~80MB
- Размерность: 384
- Скорость: ~1000 chunks/сек на CPU

Для каждого chunk генерируется вектор [384 чисел]:
```python
chunk_text = "OpenSPG is a knowledge graph engine..."
embedding = model.encode(chunk_text)
# [0.123, -0.456, 0.789, ..., 0.234]  # 384 числа
```

### 3. Хранение в SQLite

**Таблица `documents`:**
```sql
CREATE TABLE documents (
    id INTEGER PRIMARY KEY,
    url TEXT,
    title TEXT,
    app_id TEXT,
    content TEXT,
    word_count INTEGER,
    chunk_count INTEGER
);
```

**Таблица `chunks`:**
```sql
CREATE TABLE chunks (
    id INTEGER PRIMARY KEY,
    document_id INTEGER,
    chunk_index INTEGER,
    chunk_text TEXT,
    embedding BLOB  -- JSON с вектором [384 числа]
);
```

### 4. Поиск

1. Запрос → embedding: `"knowledge graph"` → `[0.1, -0.2, ...]`
2. Сравнение со всеми chunks через **cosine similarity**:
   ```python
   similarity = dot(query_vec, chunk_vec) / (norm(query_vec) * norm(chunk_vec))
   ```
3. Сортировка по similarity (0.0 - 1.0)
4. Возврат топ-N результатов

## 💡 Примеры использования

### Пример 1: Загрузка всех OpenSPG документов

```bash
cd D:\docs\DocAgent

# Windows PowerShell
Get-ChildItem -Path knowledge_base\openspg\*.md | ForEach-Object {
    python scripts/pipeline_lite.py load $_.FullName --app openspg
}

# Linux/Mac
for file in knowledge_base/openspg/*.md; do
    python scripts/pipeline_lite.py load "$file" --app openspg
done
```

### Пример 2: Поиск с фильтрацией

```python
from scripts.pipeline_lite import DocumentPipelineLite

pipeline = DocumentPipelineLite(db_path="docagent_lite.db")

# Поиск
results = pipeline.search(
    query="How to build knowledge graph?",
    app_id="openspg",
    limit=5,
    min_similarity=0.5  # Только высокая релевантность
)

for result in results:
    print(f"{result['title']}: {result['similarity']:.3f}")
    print(f"  {result['chunk_text'][:150]}...")
```

### Пример 3: Программное добавление

```python
from scripts.pipeline_lite import DocumentPipelineLite

pipeline = DocumentPipelineLite()

# Добавить документ
pipeline.save_document(
    url="https://example.com/doc1",
    title="My Document",
    content="Long markdown content here...",
    app_id="myapp"
)

# Поиск
results = pipeline.search("relevant query")
```

## 🔧 Настройка

### Выбор модели embeddings

```bash
# Легкая модель (по умолчанию)
python scripts/pipeline_lite.py --model all-MiniLM-L6-v2 load file.md

# Более точная модель (больше размер)
python scripts/pipeline_lite.py --model all-mpnet-base-v2 load file.md

# Многоязычная модель
python scripts/pipeline_lite.py --model paraphrase-multilingual-MiniLM-L12-v2 load file.md
```

**Сравнение моделей:**

| Модель | Размер | Dim | Скорость | Качество |
|--------|--------|-----|----------|----------|
| all-MiniLM-L6-v2 | 80MB | 384 | ⚡⚡⚡ | ⭐⭐⭐ |
| all-mpnet-base-v2 | 420MB | 768 | ⚡⚡ | ⭐⭐⭐⭐ |
| paraphrase-multilingual-MiniLM-L12-v2 | 470MB | 384 | ⚡⚡ | ⭐⭐⭐⭐ |

### Изменение размера chunks

Измените в коде `pipeline_lite.py`:

```python
pipeline = DocumentPipelineLite(
    chunk_size=1000,  # Больше chunks = больше контекста
    chunk_overlap=100  # Больше overlap = меньше потерь
)
```

**Рекомендации:**
- Короткие chunks (300-500) - лучше точность
- Длинные chunks (1000-2000) - больше контекста
- Overlap 10-20% от chunk_size

## 📈 Производительность

### Тесты на локальном компьютере

**Hardware**: Intel i5, 16GB RAM, без GPU

| Операция | Скорость |
|----------|----------|
| Загрузка модели | ~3 сек |
| Chunking 10K слов | ~0.1 сек |
| Embeddings 20 chunks | ~0.5 сек |
| Сохранение в SQLite | ~0.1 сек |
| Поиск по 1000 chunks | ~2 сек |

**Пример**: Документ OpenSPG (24 страницы, 16K слов)
- Chunking: 32 chunks
- Embeddings: ~1.5 секунд
- Сохранение: ~0.2 секунды
- **Итого: ~2 секунды на документ**

## 🔍 Качество поиска

### Пример реальных результатов

**Запрос**: `"How to define schema in OpenSPG?"`

```
1. [OpenSPG Schema Guide] (0.847)
   Schema definition in OpenSPG allows you to model domain knowledge using SPO triples...

2. [Quick Start Tutorial] (0.782)
   To get started with schemas, first define your entity types and their properties...

3. [Advanced Concepts] (0.691)
   Schema evolution and versioning are supported through migration scripts...
```

**Similarity score интерпретация:**
- `0.9-1.0` - Почти идентичный текст
- `0.7-0.9` - Высокая релевантность
- `0.5-0.7` - Средняя релевантность
- `0.3-0.5` - Низкая релевантность
- `<0.3` - Нерелевантно (фильтруется)

## 🧪 Эксперименты

### Эксперимент 1: Размер chunks

```bash
# Тест 1: Маленькие chunks (300 слов)
python -c "
from scripts.pipeline_lite import DocumentPipelineLite
p = DocumentPipelineLite(chunk_size=300, chunk_overlap=30)
p.load_from_file('knowledge_base/openspg/intro.md', app_id='test1')
results = p.search('knowledge graph', app_id='test1')
print(f'Results: {len(results)}, Avg similarity: {sum(r[\"similarity\"] for r in results)/len(results):.3f}')
"

# Тест 2: Большие chunks (1000 слов)
python -c "
from scripts.pipeline_lite import DocumentPipelineLite
p = DocumentPipelineLite(chunk_size=1000, chunk_overlap=100)
p.load_from_file('knowledge_base/openspg/intro.md', app_id='test2')
results = p.search('knowledge graph', app_id='test2')
print(f'Results: {len(results)}, Avg similarity: {sum(r[\"similarity\"] for r in results)/len(results):.3f}')
"
```

### Эксперимент 2: Разные модели

```bash
# all-MiniLM-L6-v2 (легкая)
python scripts/pipeline_lite.py --model all-MiniLM-L6-v2 --db test_mini.db \
  load knowledge_base/openspg/intro.md

python scripts/pipeline_lite.py --db test_mini.db search "schema definition"

# all-mpnet-base-v2 (точная)
python scripts/pipeline_lite.py --model all-mpnet-base-v2 --db test_mpnet.db \
  load knowledge_base/openspg/intro.md

python scripts/pipeline_lite.py --db test_mpnet.db search "schema definition"
```

### Эксперимент 3: Multilingual

```bash
# Английский + Китайский
python scripts/pipeline_lite.py \
  --model paraphrase-multilingual-MiniLM-L12-v2 \
  load knowledge_base/openspg/intro.md

# Поиск на русском
python scripts/pipeline_lite.py search "определение схемы знаний"
```

## 🔄 Миграция на production

Когда эксперименты закончены, легко мигрировать:

### SQLite → PostgreSQL + pgvector

```python
# 1. Экспорт из SQLite
import sqlite3
import psycopg2

sqlite_conn = sqlite3.connect("docagent_lite.db")
pg_conn = psycopg2.connect("postgresql://...")

# 2. Копирование данных
for doc in sqlite_conn.execute("SELECT * FROM documents"):
    pg_conn.execute("INSERT INTO documents VALUES (...)")

# 3. Embeddings в pgvector
for chunk in sqlite_conn.execute("SELECT * FROM chunks"):
    embedding = json.loads(chunk['embedding'])
    pg_conn.execute(
        "INSERT INTO chunks (embedding) VALUES (%s::vector)",
        (embedding,)
    )
```

### sentence-transformers → OpenAI API

```python
# Замена модели
# OLD:
model = SentenceTransformer("all-MiniLM-L6-v2")
embedding = model.encode(text)

# NEW:
import openai
response = openai.Embedding.create(
    model="text-embedding-ada-002",
    input=text
)
embedding = response['data'][0]['embedding']
```

## 🐛 Troubleshooting

### Проблема: Модель не загружается

```
OSError: Can't load tokenizer for 'all-MiniLM-L6-v2'
```

**Решение**: Ручная загрузка
```bash
python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')"
```

### Проблема: Медленный поиск

Если chunks > 10,000, поиск становится медленным.

**Решения:**
1. Фильтрация по `app_id` перед поиском
2. Использование FAISS для векторного индекса
3. Миграция на PostgreSQL + pgvector

### Проблема: Низкое качество поиска

**Причины:**
- Слишком большие chunks (>1000 слов)
- Слишком маленькие chunks (<200 слов)
- Неправильная модель для языка

**Решения:**
- Оптимальный размер: 400-600 слов
- Overlap: 10-15%
- Multilingual модель для non-English

## 📚 Дальнейшие улучшения

### FAISS для быстрого поиска

```python
import faiss

# Создание индекса
index = faiss.IndexFlatIP(384)  # Inner Product ~ Cosine
embeddings_matrix = np.array([...])  # Все embeddings
index.add(embeddings_matrix)

# Быстрый поиск
query_vec = model.encode([query])[0]
D, I = index.search(query_vec.reshape(1, -1), k=10)
```

### Гибридный поиск (BM25 + Vector)

```python
from rank_bm25 import BM25Okapi

# BM25 для keyword search
corpus = [chunk['text'].split() for chunk in chunks]
bm25 = BM25Okapi(corpus)

# Комбинация scores
keyword_scores = bm25.get_scores(query.split())
vector_scores = [cosine_sim(query_vec, chunk_vec) for chunk_vec in chunk_vecs]

# Weighted combination
final_scores = 0.3 * keyword_scores + 0.7 * vector_scores
```

### Reranking с cross-encoder

```python
from sentence_transformers import CrossEncoder

reranker = CrossEncoder('cross-encoder/ms-marco-MiniLM-L-12-v2')

# Первичный поиск (top 100)
candidates = pipeline.search(query, limit=100)

# Reranking (top 10)
pairs = [(query, c['chunk_text']) for c in candidates]
scores = reranker.predict(pairs)
reranked = sorted(zip(candidates, scores), key=lambda x: x[1], reverse=True)[:10]
```

## 📖 Дополнительная информация

- **sentence-transformers**: https://www.sbert.net/
- **Модели**: https://www.sbert.net/docs/pretrained_models.html
- **Chunking стратегии**: https://www.pinecone.io/learn/chunking-strategies/
- **Cosine similarity**: https://en.wikipedia.org/wiki/Cosine_similarity

---

**✨ Готов к экспериментам! Запустите `python scripts/pipeline_lite.py --help` для начала.**
