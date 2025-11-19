# Развертывание DocAgent на сервере

## Быстрая установка (Ubuntu/Debian)

### 1. Подготовка сервера

```bash
# SSH подключение к серверу
ssh user@your-server-ip

# Обновление системы
sudo apt-get update
sudo apt-get upgrade -y

# Установка необходимых пакетов
sudo apt-get install -y python3 python3-pip python3-venv git curl wget
```

### 2. Автоматическая установка

```bash
# Скачать и запустить скрипт установки
curl -fsSL https://raw.githubusercontent.com/leval907/docagent/main/install.sh -o install.sh
chmod +x install.sh
./install.sh
```

### 3. Настройка переменных окружения

```bash
cd docagent
nano .env
```

Добавьте ваши credentials:

```bash
# S3 Configuration (Beget)
AWS_ACCESS_KEY_ID=JQDHVXZY7XFWUHF8LV0S
AWS_SECRET_ACCESS_KEY=pjVG1Zt5G6y8N8eYAmPnKcnnPpfxB3KVCcFrEyfk
S3_ENDPOINT=https://s3.ru1.storage.beget.cloud
S3_BUCKET=db6a1f644d97-la-ducem1

# PostgreSQL (опционально)
PG_HOST=localhost
PG_PORT=5432
PG_DATABASE=docagent
PG_USER=postgres
PG_PASSWORD=your_password

# Encoding
PYTHONIOENCODING=utf-8
```

### 4. Запуск краулера

```bash
# Активировать виртуальное окружение
source venv/bin/activate

# Запустить краулер с загрузкой в S3
python scripts/crawl_and_clean.py --app openspg \
  --s3-bucket db6a1f644d97-la-ducem1 \
  --s3-endpoint https://s3.ru1.storage.beget.cloud
```

## Ручная установка (пошагово)

### Шаг 1: Клонирование репозитория

```bash
git clone https://github.com/leval907/docagent.git
cd docagent
```

### Шаг 2: Создание виртуального окружения

```bash
python3 -m venv venv
source venv/bin/activate
```

### Шаг 3: Установка зависимостей

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### Шаг 4: Установка Playwright

```bash
playwright install chromium
playwright install-deps chromium
```

### Шаг 5: Конфигурация

```bash
cp .env.example .env
nano .env
```

### Шаг 6: Создание директорий

```bash
mkdir -p knowledge_base logs
```

## Использование с Docker

### Вариант 1: Docker Compose (рекомендуется)

```bash
# С PostgreSQL
docker-compose up -d

# Только краулер
docker-compose up crawler
```

### Вариант 2: Простой Docker

```bash
# Сборка образа
docker build -t docagent .

# Запуск
docker run -it --rm \
  -e AWS_ACCESS_KEY_ID=JQDHVXZY7XFWUHF8LV0S \
  -e AWS_SECRET_ACCESS_KEY=pjVG1Zt5G6y8N8eYAmPnKcnnPpfxB3KVCcFrEyfk \
  -e S3_ENDPOINT=https://s3.ru1.storage.beget.cloud \
  -e S3_BUCKET=db6a1f644d97-la-ducem1 \
  -v $(pwd)/knowledge_base:/app/knowledge_base \
  docagent \
  python scripts/crawl_and_clean.py --app openspg \
    --s3-bucket db6a1f644d97-la-ducem1 \
    --s3-endpoint https://s3.ru1.storage.beget.cloud
```

## Запуск по расписанию (cron)

### Создание скрипта

```bash
nano ~/run_crawler.sh
```

Содержимое:

```bash
#!/bin/bash
cd /path/to/docagent
source venv/bin/activate

export AWS_ACCESS_KEY_ID=JQDHVXZY7XFWUHF8LV0S
export AWS_SECRET_ACCESS_KEY=pjVG1Zt5G6y8N8eYAmPnKcnnPpfxB3KVCcFrEyfk
export PYTHONIOENCODING=utf-8

python scripts/crawl_and_clean.py --app openspg \
  --s3-bucket db6a1f644d97-la-ducem1 \
  --s3-endpoint https://s3.ru1.storage.beget.cloud \
  >> logs/crawler.log 2>&1

echo "Crawl completed at $(date)" >> logs/crawler.log
```

Сделать исполняемым:

```bash
chmod +x ~/run_crawler.sh
```

### Настройка cron

```bash
crontab -e
```

Добавить задачу (например, каждый день в 2:00):

```cron
0 2 * * * /home/user/run_crawler.sh
```

Или каждые 6 часов:

```cron
0 */6 * * * /home/user/run_crawler.sh
```

## Проверка работы S3

### Тест подключения

```bash
python3 << EOF
import boto3
from botocore.config import Config

s3 = boto3.client(
    's3',
    endpoint_url='https://s3.ru1.storage.beget.cloud',
    aws_access_key_id='JQDHVXZY7XFWUHF8LV0S',
    aws_secret_access_key='pjVG1Zt5G6y8N8eYAmPnKcnnPpfxB3KVCcFrEyfk',
    config=Config(
        signature_version='s3v4',
        s3={'addressing_style': 'path'}
    )
)

# Список файлов в бакете
response = s3.list_objects_v2(Bucket='db6a1f644d97-la-ducem1')
print(f"Files in bucket: {response.get('KeyCount', 0)}")
for obj in response.get('Contents', [])[:5]:
    print(f"  - {obj['Key']} ({obj['Size']} bytes)")
EOF
```

## Настройка PostgreSQL (опционально)

### Установка PostgreSQL

```bash
sudo apt-get install -y postgresql postgresql-contrib
```

### Создание базы данных

```bash
sudo -u postgres psql

CREATE DATABASE docagent;
CREATE USER docagent_user WITH PASSWORD 'your_password';
GRANT ALL PRIVILEGES ON DATABASE docagent TO docagent_user;
\q
```

### Создание таблиц

```bash
source venv/bin/activate
python << EOF
import psycopg2

conn = psycopg2.connect(
    host='localhost',
    database='docagent',
    user='docagent_user',
    password='your_password'
)

cur = conn.cursor()

# Таблица документов
cur.execute('''
CREATE TABLE IF NOT EXISTS documents (
    id SERIAL PRIMARY KEY,
    app_id VARCHAR(50) NOT NULL,
    url TEXT NOT NULL UNIQUE,
    title TEXT,
    s3_path TEXT,
    file_hash VARCHAR(64),
    word_count INTEGER,
    metadata JSONB,
    crawled_at TIMESTAMP,
    uploaded_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
)
''')

# Таблица статистики
cur.execute('''
CREATE TABLE IF NOT EXISTS crawl_stats (
    id SERIAL PRIMARY KEY,
    app_id VARCHAR(50) NOT NULL,
    pages_crawled INTEGER,
    pages_cleaned INTEGER,
    pages_uploaded INTEGER,
    total_words INTEGER,
    duration_seconds FLOAT,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
)
''')

conn.commit()
cur.close()
conn.close()

print("✅ Tables created successfully!")
EOF
```

### Запуск с PostgreSQL

```bash
python scripts/crawl_and_clean.py --app openspg \
  --s3-bucket db6a1f644d97-la-ducem1 \
  --s3-endpoint https://s3.ru1.storage.beget.cloud \
  --pg-host localhost \
  --pg-database docagent \
  --pg-user docagent_user \
  --pg-password your_password
```

## Мониторинг

### Просмотр логов

```bash
# Последние 50 строк
tail -n 50 logs/crawler.log

# В реальном времени
tail -f logs/crawler.log
```

### Проверка процессов

```bash
# Найти запущенные краулеры
ps aux | grep crawl_and_clean

# Проверка использования ресурсов
htop
```

### Проверка содержимого S3

```bash
# Установить AWS CLI (опционально)
sudo apt-get install -y awscli

# Настроить профиль для Beget
aws configure --profile beget
# AWS Access Key ID: JQDHVXZY7XFWUHF8LV0S
# AWS Secret Access Key: pjVG1Zt5G6y8N8eYAmPnKcnnPpfxB3KVCcFrEyfk
# Region: ru1

# Список файлов
aws s3 ls s3://db6a1f644d97-la-ducem1/openspg/ \
  --endpoint-url https://s3.ru1.storage.beget.cloud \
  --profile beget
```

## Troubleshooting

### Ошибка: playwright не установлен

```bash
playwright install chromium
playwright install-deps chromium
```

### Ошибка: XAmzContentSHA256Mismatch

Уже исправлено в коде. Используется `ChecksumSHA256` с base64.

### Ошибка: UnicodeDecodeError

```bash
export PYTHONIOENCODING=utf-8
```

Или в `.env`:
```
PYTHONIOENCODING=utf-8
```

### Ошибка: Permission denied

```bash
chmod +x install.sh
chmod +x run_crawler.sh
```

### Недостаточно памяти

Добавить swap:

```bash
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
```

## Безопасность

### 1. Защита credentials

```bash
# Установить правильные права на .env
chmod 600 .env

# Не коммитить в git
echo ".env" >> .gitignore
```

### 2. Firewall

```bash
# Открыть только необходимые порты
sudo ufw allow 22/tcp  # SSH
sudo ufw enable
```

### 3. Автоматические обновления

```bash
sudo apt-get install -y unattended-upgrades
sudo dpkg-reconfigure --priority=low unattended-upgrades
```

## Производительность

### Многопоточный краулинг

В `config/sources.yaml` увеличьте `max_pages`:

```yaml
openspg:
  max_pages: 200  # Больше страниц за раз
```

### Батч-обработка нескольких сайтов

Создайте скрипт `run_all.sh`:

```bash
#!/bin/bash
apps=("openspg" "nocodb" "python_docs")

for app in "${apps[@]}"; do
    echo "Processing $app..."
    python scripts/crawl_and_clean.py --app "$app" \
      --s3-bucket db6a1f644d97-la-ducem1 \
      --s3-endpoint https://s3.ru1.storage.beget.cloud
done
```

## Контакты и поддержка

- GitHub: https://github.com/leval907/docagent
- Issues: https://github.com/leval907/docagent/issues

---

**Готово! Сервер настроен для автоматического краулинга документации в S3 🚀**
