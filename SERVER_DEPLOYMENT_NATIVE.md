# 🖥️ Развертывание на сервере без Docker

## 📊 Требования к серверу

### Минимальная конфигурация (Lite режим)

```
CPU:     2 cores
RAM:     4 GB
Disk:    20 GB SSD
OS:      Ubuntu 20.04+ / Debian 11+
Network: 100 Mbps
```

**Достаточно для:**
- SQLite база данных
- sentence-transformers (локальные embeddings)
- До 10,000 документов
- 1-2 concurrent users

### Рекомендованная конфигурация (Production)

```
CPU:     4-8 cores
RAM:     16 GB
Disk:    100 GB SSD (NVMe)
OS:      Ubuntu 22.04 LTS
Network: 1 Gbps
```

**Поддерживает:**
- PostgreSQL 18 + pgvector
- ChromaDB для векторов
- Prefect + FastAPI
- До 100,000 документов
- 10+ concurrent users

## 🚀 Быстрая установка

### 1. Подключение к серверу

```bash
ssh user@your-server-ip
```

### 2. Загрузка скрипта установки

```bash
# Вариант 1: Клонирование репозитория
git clone https://github.com/leval907/docagent.git /tmp/docagent
cd /tmp/docagent

# Вариант 2: Прямая загрузка
curl -O https://raw.githubusercontent.com/leval907/docagent/main/install_server.sh
chmod +x install_server.sh
```

### 3. Запуск установки

**Для Lite режима (рекомендуется для начала):**
```bash
sudo ./install_server.sh lite
```

**Для Production режима:**
```bash
sudo ./install_server.sh full
```

### 4. Конфигурация

```bash
sudo nano /opt/docagent/.env
```

Обновите настройки:
```bash
# S3 (если используете)
AWS_ACCESS_KEY_ID=JQDHVXZY7XFWUHF8LV0S
AWS_SECRET_ACCESS_KEY=pjVG1Zt5G6y8N8eYAmPnKcnnPpfxB3KVCcFrEyfk
S3_ENDPOINT=https://s3.ru1.storage.beget.cloud
S3_BUCKET=db6a1f644d97-la-ducem1

# PostgreSQL (для production)
POSTGRES_PASSWORD=your_secure_password_here

# SQLite путь (для lite)
SQLITE_PATH=/opt/docagent/data/sqlite/docagent_lite.db
```

## 📦 Что устанавливается

### Lite режим
- ✅ Python 3.11 + venv
- ✅ sentence-transformers (80-300 MB)
- ✅ Playwright + Chromium
- ✅ SQLite (встроенный)
- ✅ Cron задачи для автоматизации

**Используемые порты:** нет (все локально)

### Production режим
Все из Lite режима плюс:
- ✅ PostgreSQL 18 + pgvector
- ✅ FastAPI REST API (порт 8080)
- ✅ Prefect Server (порт 4200)
- ✅ Systemd сервисы

**Используемые порты:**
- 8080 - FastAPI REST API
- 4200 - Prefect UI (внутренний)
- 5432 - PostgreSQL (внутренний, не открыт наружу)

## 🧪 Тестирование установки

### Lite режим

```bash
# Активировать окружение
source /opt/docagent/venv/bin/activate
cd /opt/docagent

# Краулинг документации
python scripts/crawler_crawl4ai.py --app duckdb

# Загрузка в SQLite
for file in knowledge_base/duckdb/*.md; do
    python scripts/pipeline_lite.py load "$file" --app duckdb
done

# Проверка статистики
python scripts/pipeline_lite.py stats

# Тестовый поиск
python scripts/pipeline_lite.py search "SQL query" --app duckdb --limit 5
```

**Ожидаемый результат:**
```
📊 Статистика
Документов: 100
Chunks: 500-1000

🔍 Найдено результатов: 5

1. [DuckDB SQL Reference] (0.847)
   Текст: SQL queries in DuckDB support...
```

### Production режим

```bash
# Проверка PostgreSQL
sudo -u postgres psql -d docagent -c "SELECT version();"

# Проверка сервисов
sudo systemctl status docagent-api
sudo systemctl status docagent-prefect

# Проверка API
curl http://localhost:8080/health

# Проверка базы
curl http://localhost:8080/stats
```

**Ожидаемый результат:**
```json
{
  "status": "healthy",
  "postgresql": "connected",
  "chromadb": "connected"
}
```

## 📁 Структура на сервере

```
/opt/docagent/
├── venv/                    # Python окружение
├── scripts/
│   ├── pipeline_lite.py     # Lite pipeline
│   ├── crawler_crawl4ai.py  # Crawler
│   └── daily_crawl.sh       # Cron скрипт
├── api/
│   └── main.py              # FastAPI (production)
├── workflows/
│   └── prefect_flows.py     # Prefect flows (production)
├── knowledge_base/
│   ├── duckdb/              # Скачанные документы
│   ├── openspg/
│   └── ...
├── data/
│   ├── sqlite/
│   │   └── docagent_lite.db # SQLite БД (lite)
│   ├── chromadb/            # ChromaDB data (production)
│   └── duckdb/              # DuckDB analytics (production)
├── logs/
│   ├── crawl.log
│   ├── pipeline.log
│   └── daily.log
├── backups/                 # Бэкапы БД
├── config/
│   └── sources.yaml         # Конфигурация источников
├── .env                     # Credentials (НЕ в git!)
└── README.md
```

## 🔄 Ежедневная автоматизация

Скрипт установки настраивает cron задачу:

```cron
0 2 * * * /opt/docagent/scripts/daily_crawl.sh
```

Это выполняет:
1. Краулинг всех enabled источников
2. Обработка и chunking
3. Генерация embeddings
4. Загрузка в базу данных

**Логи:** `/opt/docagent/logs/daily.log`

## 🔧 Управление сервисами

### Lite режим (ручной запуск)

```bash
cd /opt/docagent
source venv/bin/activate

# Краулинг
python scripts/crawler_crawl4ai.py --app duckdb

# Обработка
python scripts/pipeline_lite.py load knowledge_base/duckdb/*.md --app duckdb

# Поиск
python scripts/pipeline_lite.py search "your query"
```

### Production режим (systemd сервисы)

```bash
# Запуск сервисов
sudo systemctl start docagent-api
sudo systemctl start docagent-prefect

# Остановка
sudo systemctl stop docagent-api
sudo systemctl stop docagent-prefect

# Перезапуск
sudo systemctl restart docagent-api

# Просмотр логов
sudo journalctl -u docagent-api -f
sudo journalctl -u docagent-prefect -f

# Автозапуск при загрузке
sudo systemctl enable docagent-api
```

## 📊 Мониторинг

### Проверка ресурсов

```bash
# CPU и Memory
htop

# Disk usage
df -h /opt/docagent

# PostgreSQL (production)
sudo -u postgres psql -d docagent -c "
SELECT 
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
FROM pg_tables 
WHERE schemaname = 'public' 
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
"

# SQLite размер (lite)
ls -lh /opt/docagent/data/sqlite/docagent_lite.db
```

### Логи

```bash
# Последние краулинги
tail -f /opt/docagent/logs/crawl.log

# Pipeline обработка
tail -f /opt/docagent/logs/pipeline.log

# Ежедневные задачи
tail -f /opt/docagent/logs/daily.log

# API логи (production)
sudo journalctl -u docagent-api --since "1 hour ago"
```

## 🔒 Безопасность

### 1. Firewall

```bash
# Установка UFW
sudo apt install ufw

# Разрешить SSH
sudo ufw allow 22/tcp

# Разрешить API (опционально)
sudo ufw allow 8080/tcp

# Заблокировать PostgreSQL снаружи
sudo ufw deny 5432/tcp

# Включить firewall
sudo ufw enable
```

### 2. Nginx как reverse proxy (рекомендуется)

```bash
sudo apt install nginx certbot python3-certbot-nginx

# Создать конфиг
sudo nano /etc/nginx/sites-available/docagent
```

```nginx
server {
    listen 80;
    server_name api.yourdomain.com;
    
    location / {
        proxy_pass http://localhost:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
```

```bash
# Активировать
sudo ln -s /etc/nginx/sites-available/docagent /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx

# SSL сертификат
sudo certbot --nginx -d api.yourdomain.com
```

### 3. Права доступа

```bash
# Проверка прав
ls -la /opt/docagent

# Файлы должны принадлежать пользователю (не root)
# .env должен быть 600 (только владелец читает/пишет)
```

## 💾 Бэкапы

### Автоматический бэкап

```bash
# Создать скрипт бэкапа
sudo nano /opt/docagent/scripts/backup.sh
```

```bash
#!/bin/bash
BACKUP_DIR="/opt/docagent/backups"
DATE=$(date +%Y%m%d_%H%M%S)

# SQLite backup (lite mode)
if [ -f "/opt/docagent/data/sqlite/docagent_lite.db" ]; then
    cp /opt/docagent/data/sqlite/docagent_lite.db \
       $BACKUP_DIR/docagent_lite_$DATE.db
fi

# PostgreSQL backup (production)
if command -v pg_dump &> /dev/null; then
    sudo -u postgres pg_dump docagent | gzip > \
        $BACKUP_DIR/postgres_$DATE.sql.gz
fi

# Удалить старые бэкапы (>7 дней)
find $BACKUP_DIR -name "*.db" -mtime +7 -delete
find $BACKUP_DIR -name "*.sql.gz" -mtime +7 -delete

echo "$(date): Backup completed" >> /opt/docagent/logs/backup.log
```

```bash
chmod +x /opt/docagent/scripts/backup.sh

# Добавить в cron (ежедневно в 3:00)
(crontab -l 2>/dev/null; echo "0 3 * * * /opt/docagent/scripts/backup.sh") | crontab -
```

## 🔄 Обновление

```bash
cd /opt/docagent
source venv/bin/activate

# Получить обновления
git pull origin main

# Обновить зависимости
pip install -r requirements.txt --upgrade

# Перезапустить сервисы (production)
sudo systemctl restart docagent-api
sudo systemctl restart docagent-prefect
```

## 🐛 Troubleshooting

### Проблема: Недостаточно памяти

**Симптомы:**
```
MemoryError: Unable to allocate array
OOM killed
```

**Решения:**
1. Уменьшить `chunk_size` в pipeline_lite.py
2. Использовать более легкую модель: `all-MiniLM-L6-v2` (80MB)
3. Добавить swap:
```bash
sudo fallocate -l 4G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
```

### Проблема: Playwright не работает

**Симптомы:**
```
Executable doesn't exist at /home/user/.cache/ms-playwright/chromium-...
```

**Решение:**
```bash
source /opt/docagent/venv/bin/activate
playwright install chromium
playwright install-deps
```

### Проблема: PostgreSQL не подключается

**Решение:**
```bash
# Проверить статус
sudo systemctl status postgresql

# Проверить доступ
sudo -u postgres psql -d docagent -c "SELECT 1;"

# Проверить пароль в .env
cat /opt/docagent/.env | grep POSTGRES_PASSWORD
```

## 📈 Оптимизация производительности

### PostgreSQL tuning

```bash
sudo nano /etc/postgresql/18/main/postgresql.conf
```

```ini
# Memory
shared_buffers = 4GB              # 25% от RAM
effective_cache_size = 12GB       # 75% от RAM
work_mem = 64MB
maintenance_work_mem = 1GB

# Connections
max_connections = 100

# WAL
wal_buffers = 16MB
checkpoint_completion_target = 0.9

# Planner
random_page_cost = 1.1            # Для SSD
effective_io_concurrency = 200    # Для SSD
```

```bash
sudo systemctl restart postgresql
```

### Индексы для поиска

```sql
-- Подключиться к БД
sudo -u postgres psql -d docagent

-- Создать индексы
CREATE INDEX CONCURRENTLY idx_documents_app_created 
    ON documents(app_id, created_at DESC);

CREATE INDEX CONCURRENTLY idx_chunks_document_app 
    ON chunks(document_id);

-- HNSW индекс для векторного поиска (pgvector)
CREATE INDEX CONCURRENTLY idx_embeddings_vector 
    ON document_embeddings 
    USING hnsw (embedding vector_cosine_ops);
```

## 🎓 Дополнительная информация

- **Документация**: `/opt/docagent/README.md`
- **GitHub**: https://github.com/leval907/docagent
- **Логи**: `/opt/docagent/logs/`
- **Бэкапы**: `/opt/docagent/backups/`

---

**✅ Готово! Сервер настроен и готов к использованию.**

Для вопросов и поддержки создайте issue на GitHub.
