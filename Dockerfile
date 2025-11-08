# DocAgent Parser - Minimal Docker Image
FROM python:3.11-slim

# Установить только git (нужен для клонирования markdown-crawler)
RUN apt-get update && apt-get install -y \
    git \
    && rm -rf /var/lib/apt/lists/*

# Создать рабочую директорию
WORKDIR /app

# Скопировать requirements
COPY requirements.txt .

# Установить Python зависимости
RUN pip install --no-cache-dir -r requirements.txt

# Клонировать markdown-crawler
RUN mkdir -p tools && \
    cd tools && \
    git clone https://github.com/paulpierre/markdown-crawler.git && \
    cd markdown-crawler && \
    pip install --no-cache-dir -r requirements.txt

# Скопировать только необходимые файлы проекта
COPY scripts/ ./scripts/
COPY config/ ./config/

# Создать директории для вывода
RUN mkdir -p /app/knowledge_base /app/logs

# Установить переменные окружения
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

# Точка входа
ENTRYPOINT ["python"]
CMD ["scripts/wrapper_crawler.py", "--help"]
