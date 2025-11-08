# Docker Setup для DocAgent с PostgreSQL 18 + pgvector

## Быстрый старт

### 1. Создание структуры директорий

```bash
cd /opt
sudo mkdir -p docagent/{pgdata,knowledge_base,logs,backups}
cd docagent
```

### 2. Клонирование репозитория

```bash
git clone https://github.com/leval907/docagent.git .
```

### 3. Настройка переменных окружения

```bash
cp .env.example .env
nano .env
```

Обновите credentials:

```bash
# S3 Configuration
AWS_ACCESS_KEY_ID=JQDHVXZY7XFWUHF8LV0S
AWS_SECRET_ACCESS_KEY=pjVG1Zt5G6y8N8eYAmPnKcnnPpfxB3KVCcFrEyfk
S3_ENDPOINT=https://s3.ru1.storage.beget.cloud
S3_BUCKET=db6a1f644d97-la-ducem1

# PostgreSQL Configuration
POSTGRES_USER=docagent
POSTGRES_PASSWORD=secure_pass_2025
POSTGRES_DB=docagent
POSTGRES_PORT=5436
POSTGRES_DATA_PATH=/opt/docagent/pgdata

# Network Configuration
NETWORK_NAME=ducem-net
NETWORK_EXTERNAL=true
```

### 4. Создание Docker сети (если не существует)

```bash
# Проверить существующие сети
docker network ls | grep ducem-net

# Если сети нет, создать:
docker network create ducem-net

# Если сеть уже есть, пропустите этот шаг
```

### 5. Запуск PostgreSQL

```bash
# Только PostgreSQL
docker compose up -d postgres18

# Проверить запуск
docker ps
docker logs docagent-postgres
```

### 6. Инициализация БД

```bash
# Подключиться к PostgreSQL
docker exec -it docagent-postgres psql -U docagent -d docagent

# Проверить расширение pgvector
\dx

# Проверить таблицы
\dt

# Выйти
\q
```

### 7. Запуск краулера

```bash
# Разовый запуск
docker compose --profile crawler run --rm crawler

# Или с параметрами
docker compose --profile crawler run --rm -e APP=openspg crawler
```

## Полная конфигурация

### docker-compose.yml

```yaml
version: "3.9"

services:
  postgres18:
    image: ankane/pgvector:latest
    container_name: docagent-postgres
    restart: always
    environment:
      POSTGRES_USER: docagent
      POSTGRES_PASSWORD: secure_pass_2025
      POSTGRES_DB: docagent
    ports:
      - "5436:5432"
    volumes:
      - /opt/docagent/pgdata:/var/lib/postgresql/data
      - ./init-db.sql:/docker-entrypoint-initdb.d/init-db.sql:ro
    networks:
      - ducem-net

  crawler:
    build: .
    container_name: docagent-crawler
    depends_on:
      postgres18:
        condition: service_healthy
    environment:
      - AWS_ACCESS_KEY_ID=${AWS_ACCESS_KEY_ID}
      - AWS_SECRET_ACCESS_KEY=${AWS_SECRET_ACCESS_KEY}
      - S3_ENDPOINT=${S3_ENDPOINT}
      - S3_BUCKET=${S3_BUCKET}
    volumes:
      - ./knowledge_base:/app/knowledge_base
      - ./logs:/app/logs
    networks:
      - ducem-net
    profiles:
      - crawler

networks:
  ducem-net:
    external: true
```

## Использование

### Запуск PostgreSQL

```bash
# Старт
docker compose up -d postgres18

# Остановка
docker compose stop postgres18

# Рестарт
docker compose restart postgres18

# Логи
docker logs -f docagent-postgres
```

### Запуск краулера

```bash
# OpenSPG
docker compose --profile crawler run --rm \
  -e APP=openspg \
  crawler

# NocoDB
docker compose --profile crawler run --rm \
  -e APP=nocodb \
  crawler

# Python Docs
docker compose --profile crawler run --rm \
  -e APP=python_docs \
  crawler
```

### Подключение к PostgreSQL

#### Из хоста

```bash
# psql
psql -h localhost -p 5436 -U docagent -d docagent

# Connection string
postgresql://docagent:secure_pass_2025@localhost:5436/docagent
```

#### Из других Docker контейнеров в сети ducem-net

```bash
# Connection string
postgresql://docagent:secure_pass_2025@docagent-postgres:5432/docagent
```

#### Python пример

```python
import psycopg2

conn = psycopg2.connect(
    host='localhost',  # или 'docagent-postgres' из Docker
    port=5436,         # или 5432 из Docker
    database='docagent',
    user='docagent',
    password='secure_pass_2025'
)

cur = conn.cursor()
cur.execute('SELECT COUNT(*) FROM documents')
print(f"Total documents: {cur.fetchone()[0]}")
cur.close()
conn.close()
```

## Интеграция с Flowise и n8n

### Flowise

В Flowise используйте PostgreSQL как vector store:

```yaml
Host: docagent-postgres  # если Flowise в ducem-net
Port: 5432
Database: docagent
User: docagent
Password: secure_pass_2025
```

### n8n

В n8n создайте Postgres Credential:

```yaml
Host: docagent-postgres
Port: 5432
Database: docagent
User: docagent
Password: secure_pass_2025
```

### OpenSPG

OpenSPG может использовать ту же БД для хранения knowledge graph:

```bash
POSTGRES_URL=postgresql://docagent:secure_pass_2025@docagent-postgres:5432/docagent
```

## Бэкапы

### Автоматический бэкап

Создайте скрипт `/opt/docagent/backup.sh`:

```bash
#!/bin/bash
BACKUP_DIR=/opt/docagent/backups
DATE=$(date +%Y%m%d_%H%M%S)

# Бэкап PostgreSQL
docker exec docagent-postgres pg_dump -U docagent docagent | gzip > \
  $BACKUP_DIR/docagent_$DATE.sql.gz

# Удалить старые бэкапы (старше 7 дней)
find $BACKUP_DIR -name "*.sql.gz" -mtime +7 -delete

echo "✅ Backup completed: docagent_$DATE.sql.gz"
```

Сделать исполняемым:

```bash
chmod +x /opt/docagent/backup.sh
```

### Настроить cron для ежедневного бэкапа

```bash
crontab -e
```

Добавить:

```cron
0 2 * * * /opt/docagent/backup.sh >> /opt/docagent/logs/backup.log 2>&1
```

### Восстановление из бэкапа

```bash
# Распаковать и восстановить
gunzip -c /opt/docagent/backups/docagent_20250109_020000.sql.gz | \
  docker exec -i docagent-postgres psql -U docagent -d docagent
```

## Мониторинг

### Проверка статуса

```bash
# Проверить работу контейнеров
docker ps

# Проверить использование ресурсов
docker stats docagent-postgres

# Проверить логи
docker logs -f docagent-postgres --tail 100
```

### Проверка БД

```bash
# Количество документов
docker exec -it docagent-postgres psql -U docagent -d docagent -c \
  "SELECT app_id, COUNT(*) FROM documents GROUP BY app_id"

# Последние 5 crawls
docker exec -it docagent-postgres psql -U docagent -d docagent -c \
  "SELECT app_id, pages_crawled, duration_seconds, completed_at FROM crawl_stats ORDER BY completed_at DESC LIMIT 5"

# Размер БД
docker exec -it docagent-postgres psql -U docagent -d docagent -c \
  "SELECT pg_size_pretty(pg_database_size('docagent'))"
```

### pgAdmin (опционально)

Добавить в `docker-compose.yml`:

```yaml
pgadmin:
  image: dpage/pgadmin4:latest
  container_name: docagent-pgadmin
  environment:
    PGADMIN_DEFAULT_EMAIL: admin@docagent.local
    PGADMIN_DEFAULT_PASSWORD: admin123
  ports:
    - "5050:80"
  networks:
    - ducem-net
```

Доступ: http://localhost:5050

## Обновление

### Обновление кода

```bash
cd /opt/docagent
git pull origin main
docker compose build crawler
```

### Обновление PostgreSQL

```bash
# Сделать бэкап!
/opt/docagent/backup.sh

# Остановить и удалить контейнер (данные сохранятся в volume)
docker compose stop postgres18
docker compose rm -f postgres18

# Обновить образ
docker compose pull postgres18

# Запустить новую версию
docker compose up -d postgres18
```

## Безопасность

### Firewall

```bash
# Разрешить доступ к PostgreSQL только с localhost
sudo ufw allow from 127.0.0.1 to any port 5436

# Или из определенной подсети
sudo ufw allow from 10.0.0.0/8 to any port 5436

# Заблокировать внешний доступ
sudo ufw deny 5436
```

### Смена пароля

```bash
# Подключиться к БД
docker exec -it docagent-postgres psql -U docagent -d docagent

# Сменить пароль
ALTER USER docagent WITH PASSWORD 'new_secure_password';
\q
```

Обновить в `.env`:

```bash
POSTGRES_PASSWORD=new_secure_password
```

### SSL/TLS (опционально)

Для продакшн-окружения настройте SSL:

```bash
# Генерация сертификатов
docker exec docagent-postgres \
  openssl req -new -x509 -days 365 -nodes \
  -text -out /var/lib/postgresql/data/server.crt \
  -keyout /var/lib/postgresql/data/server.key \
  -subj "/CN=docagent-postgres"

# Настройка прав
docker exec docagent-postgres \
  chmod 600 /var/lib/postgresql/data/server.key
```

## Troubleshooting

### PostgreSQL не запускается

```bash
# Проверить логи
docker logs docagent-postgres

# Проверить права на директорию
ls -la /opt/docagent/pgdata
sudo chown -R 999:999 /opt/docagent/pgdata
```

### Сеть ducem-net не найдена

```bash
# Создать сеть
docker network create ducem-net

# Или установить в .env:
# NETWORK_EXTERNAL=false
```

### Контейнер краулера не видит PostgreSQL

```bash
# Проверить, что оба контейнера в одной сети
docker network inspect ducem-net

# Проверить healthcheck PostgreSQL
docker inspect docagent-postgres | grep Health -A 10
```

### pgvector не работает

```bash
# Проверить установку расширения
docker exec -it docagent-postgres psql -U docagent -d docagent -c "\dx"

# Переустановить расширение
docker exec -it docagent-postgres psql -U docagent -d docagent -c \
  "DROP EXTENSION IF EXISTS vector; CREATE EXTENSION vector;"
```

## Производительность

### Настройка PostgreSQL для векторного поиска

Добавить в `docker-compose.yml`:

```yaml
postgres18:
  command: >
    postgres
    -c shared_buffers=256MB
    -c max_connections=200
    -c effective_cache_size=1GB
    -c maintenance_work_mem=128MB
    -c random_page_cost=1.1
```

### HNSW индекс для быстрого поиска

```sql
-- Уже создан в init-db.sql
CREATE INDEX idx_embeddings_vector ON document_embeddings 
USING hnsw (embedding vector_cosine_ops);
```

## Структура каталогов

```
/opt/docagent/
├── docker-compose.yml       # Docker конфигурация
├── .env                     # Переменные окружения
├── init-db.sql              # Инициализация БД
├── Dockerfile               # Образ краулера
├── pgdata/                  # PostgreSQL data (volume)
├── knowledge_base/          # Markdown файлы
├── logs/                    # Логи краулера
├── backups/                 # Бэкапы БД
├── config/
│   └── sources.yaml         # Конфигурация источников
└── scripts/
    └── crawl_and_clean.py   # Главный скрипт
```

## Полезные команды

```bash
# Запустить все сервисы
docker compose up -d

# Остановить все
docker compose down

# Пересобрать образы
docker compose build --no-cache

# Посмотреть логи всех сервисов
docker compose logs -f

# Удалить все (включая volumes)
docker compose down -v

# Зайти в контейнер PostgreSQL
docker exec -it docagent-postgres bash

# Экспорт таблицы в CSV
docker exec docagent-postgres psql -U docagent -d docagent -c \
  "COPY documents TO STDOUT WITH CSV HEADER" > documents.csv
```

---

**Готово! PostgreSQL 18 + pgvector настроен и готов к работе с Flowise, n8n и OpenSPG 🚀**
