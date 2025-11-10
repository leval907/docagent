#!/bin/bash
# DocAgent Server Installation Script
# Для Ubuntu 20.04+ / Debian 11+
#
# Использование:
#   chmod +x install_server.sh
#   sudo ./install_server.sh lite     # Для lite режима (SQLite)
#   sudo ./install_server.sh full     # Для production (PostgreSQL + все)

set -e  # Exit on error

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

MODE=${1:-lite}  # lite или full

echo -e "${GREEN}📦 DocAgent Server Installation${NC}"
echo -e "${YELLOW}Mode: ${MODE}${NC}"
echo ""

# Проверка прав root
if [ "$EUID" -ne 0 ]; then 
    echo -e "${RED}❌ Запустите с sudo${NC}"
    exit 1
fi

# Определение пользователя (не root)
REAL_USER=${SUDO_USER:-$USER}
USER_HOME=$(eval echo ~$REAL_USER)

echo -e "${GREEN}👤 User: ${REAL_USER}${NC}"
echo -e "${GREEN}🏠 Home: ${USER_HOME}${NC}"
echo ""

# ============================================
# 1. Системные пакеты
# ============================================
echo -e "${GREEN}📦 Устанавливаем системные пакеты...${NC}"

apt-get update
apt-get install -y \
    python3.11 \
    python3.11-venv \
    python3-pip \
    git \
    curl \
    wget \
    build-essential \
    libpq-dev \
    chromium-browser \
    chromium-chromedriver

# Для production режима
if [ "$MODE" = "full" ]; then
    echo -e "${GREEN}📦 Устанавливаем PostgreSQL 18...${NC}"
    
    # Добавление PostgreSQL APT repository
    sh -c 'echo "deb http://apt.postgresql.org/pub/repos/apt $(lsb_release -cs)-pgdg main" > /etc/apt/sources.list.d/pgdg.list'
    wget --quiet -O - https://www.postgresql.org/media/keys/ACCC4CF8.asc | apt-key add -
    apt-get update
    
    apt-get install -y postgresql-18 postgresql-contrib-18
    
    # pgvector extension
    apt-get install -y postgresql-18-pgvector
fi

# ============================================
# 2. Создание структуры каталогов
# ============================================
echo -e "${GREEN}📁 Создаем каталоги...${NC}"

INSTALL_DIR="/opt/docagent"
mkdir -p $INSTALL_DIR
cd $INSTALL_DIR

# Структура
mkdir -p {data,logs,backups,knowledge_base,scripts,config}
mkdir -p data/{sqlite,chromadb,duckdb}

# ============================================
# 3. Клонирование репозитория
# ============================================
echo -e "${GREEN}📥 Клонируем репозиторий...${NC}"

if [ -d "$INSTALL_DIR/.git" ]; then
    echo "Репозиторий уже существует, обновляем..."
    sudo -u $REAL_USER git pull origin main
else
    sudo -u $REAL_USER git clone https://github.com/leval907/docagent.git $INSTALL_DIR
fi

# ============================================
# 4. Python окружение
# ============================================
echo -e "${GREEN}🐍 Настраиваем Python окружение...${NC}"

# Создание venv
sudo -u $REAL_USER python3.11 -m venv $INSTALL_DIR/venv

# Активация и установка зависимостей
source $INSTALL_DIR/venv/bin/activate

# Обновление pip
pip install --upgrade pip wheel setuptools

# Основные зависимости
echo -e "${GREEN}📦 Устанавливаем Python пакеты...${NC}"
pip install -r $INSTALL_DIR/requirements.txt

# Playwright браузеры
echo -e "${GREEN}🌐 Устанавливаем Playwright браузеры...${NC}"
playwright install chromium

# Production зависимости
if [ "$MODE" = "full" ]; then
    if [ -f "$INSTALL_DIR/requirements.api.txt" ]; then
        pip install -r $INSTALL_DIR/requirements.api.txt
    fi
fi

deactivate

# ============================================
# 5. Конфигурация
# ============================================
echo -e "${GREEN}⚙️  Создаем конфигурацию...${NC}"

# .env файл
if [ ! -f "$INSTALL_DIR/.env" ]; then
    cat > $INSTALL_DIR/.env << 'EOF'
# DocAgent Configuration

# S3 Storage (Beget example)
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key
S3_ENDPOINT=https://s3.ru1.storage.beget.cloud
S3_BUCKET=your-bucket

# PostgreSQL (для production)
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_USER=docagent
POSTGRES_PASSWORD=change_me_please
POSTGRES_DB=docagent

# SQLite (для lite)
SQLITE_PATH=/opt/docagent/data/sqlite/docagent_lite.db

# ChromaDB
CHROMA_HOST=localhost
CHROMA_PORT=8000

# Prefect
PREFECT_API_URL=http://localhost:4200/api

# Модель embeddings
EMBEDDING_MODEL=all-MiniLM-L6-v2

# Paths
KNOWLEDGE_BASE_DIR=/opt/docagent/knowledge_base
LOGS_DIR=/opt/docagent/logs
EOF
    
    chown $REAL_USER:$REAL_USER $INSTALL_DIR/.env
    chmod 600 $INSTALL_DIR/.env
    
    echo -e "${YELLOW}⚠️  Отредактируйте $INSTALL_DIR/.env с вашими credentials${NC}"
fi

# ============================================
# 6. PostgreSQL настройка (для production)
# ============================================
if [ "$MODE" = "full" ]; then
    echo -e "${GREEN}🗄️  Настраиваем PostgreSQL...${NC}"
    
    # Создание пользователя и БД
    sudo -u postgres psql << EOF
-- Создание пользователя
CREATE USER docagent WITH PASSWORD 'change_me_please';

-- Создание БД
CREATE DATABASE docagent OWNER docagent;

-- Подключение к БД и установка расширений
\c docagent

-- pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Права
GRANT ALL PRIVILEGES ON DATABASE docagent TO docagent;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO docagent;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO docagent;
EOF
    
    # Инициализация схемы
    if [ -f "$INSTALL_DIR/init-db.sql" ]; then
        sudo -u postgres psql -d docagent -f $INSTALL_DIR/init-db.sql
    fi
    
    echo -e "${GREEN}✅ PostgreSQL настроен${NC}"
fi

# ============================================
# 7. Systemd сервисы (опционально)
# ============================================
echo -e "${GREEN}🔧 Создаем systemd сервисы...${NC}"

# Prefect worker (для production)
if [ "$MODE" = "full" ]; then
    cat > /etc/systemd/system/docagent-prefect.service << EOF
[Unit]
Description=DocAgent Prefect Worker
After=network.target postgresql.service

[Service]
Type=simple
User=$REAL_USER
WorkingDirectory=$INSTALL_DIR
Environment="PATH=$INSTALL_DIR/venv/bin"
EnvironmentFile=$INSTALL_DIR/.env
ExecStart=$INSTALL_DIR/venv/bin/prefect worker start --pool default-agent-pool
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

    # FastAPI (для production)
    cat > /etc/systemd/system/docagent-api.service << EOF
[Unit]
Description=DocAgent FastAPI
After=network.target postgresql.service

[Service]
Type=simple
User=$REAL_USER
WorkingDirectory=$INSTALL_DIR
Environment="PATH=$INSTALL_DIR/venv/bin"
EnvironmentFile=$INSTALL_DIR/.env
ExecStart=$INSTALL_DIR/venv/bin/uvicorn api.main:app --host 0.0.0.0 --port 8080
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

    systemctl daemon-reload
    systemctl enable docagent-prefect
    systemctl enable docagent-api
    
    echo -e "${GREEN}✅ Systemd сервисы созданы${NC}"
    echo -e "${YELLOW}Запуск: systemctl start docagent-prefect docagent-api${NC}"
fi

# ============================================
# 8. Cron задачи
# ============================================
echo -e "${GREEN}⏰ Настраиваем cron задачи...${NC}"

# Скрипт для периодического краулинга
cat > $INSTALL_DIR/scripts/daily_crawl.sh << 'EOF'
#!/bin/bash
source /opt/docagent/venv/bin/activate
source /opt/docagent/.env

cd /opt/docagent

# Краулинг всех enabled источников
python scripts/crawler_crawl4ai.py --app duckdb >> logs/crawl.log 2>&1
python scripts/crawler_crawl4ai.py --app openspg >> logs/crawl.log 2>&1

# Обработка через lite pipeline
for file in knowledge_base/duckdb/*.md; do
    python scripts/pipeline_lite.py load "$file" --app duckdb >> logs/pipeline.log 2>&1
done

echo "$(date): Daily crawl completed" >> logs/daily.log
EOF

chmod +x $INSTALL_DIR/scripts/daily_crawl.sh
chown $REAL_USER:$REAL_USER $INSTALL_DIR/scripts/daily_crawl.sh

# Добавление в crontab
(crontab -u $REAL_USER -l 2>/dev/null; echo "0 2 * * * /opt/docagent/scripts/daily_crawl.sh") | crontab -u $REAL_USER -

echo -e "${GREEN}✅ Cron задача настроена (ежедневно в 2:00)${NC}"

# ============================================
# 9. Права доступа
# ============================================
echo -e "${GREEN}🔒 Настраиваем права доступа...${NC}"

chown -R $REAL_USER:$REAL_USER $INSTALL_DIR
chmod -R 755 $INSTALL_DIR
chmod -R 700 $INSTALL_DIR/data
chmod 600 $INSTALL_DIR/.env

# ============================================
# 10. Firewall (опционально)
# ============================================
echo -e "${GREEN}🔥 Настраиваем firewall...${NC}"

if command -v ufw &> /dev/null; then
    # API порт (для production)
    if [ "$MODE" = "full" ]; then
        ufw allow 8080/tcp comment 'DocAgent API'
    fi
    
    # PostgreSQL НЕ открываем наружу
    # ufw deny 5432/tcp
    
    echo -e "${GREEN}✅ Firewall настроен${NC}"
fi

# ============================================
# Финальные инструкции
# ============================================
echo ""
echo -e "${GREEN}╔════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║   ✅ Установка завершена!                 ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${YELLOW}📝 Следующие шаги:${NC}"
echo ""
echo "1. Отредактируйте конфигурацию:"
echo "   sudo nano /opt/docagent/.env"
echo ""
echo "2. Активируйте окружение:"
echo "   source /opt/docagent/venv/bin/activate"
echo ""

if [ "$MODE" = "lite" ]; then
    echo "3. Запустите краулинг:"
    echo "   cd /opt/docagent"
    echo "   python scripts/crawler_crawl4ai.py --app duckdb"
    echo ""
    echo "4. Загрузите в SQLite:"
    echo "   python scripts/pipeline_lite.py load knowledge_base/duckdb/*.md --app duckdb"
    echo ""
    echo "5. Проверьте поиск:"
    echo "   python scripts/pipeline_lite.py search \"SQL query\" --app duckdb"
else
    echo "3. Обновите пароль PostgreSQL:"
    echo "   sudo -u postgres psql -c \"ALTER USER docagent PASSWORD 'your_secure_password';\""
    echo ""
    echo "4. Запустите сервисы:"
    echo "   sudo systemctl start docagent-prefect"
    echo "   sudo systemctl start docagent-api"
    echo ""
    echo "5. Проверьте статус:"
    echo "   sudo systemctl status docagent-prefect"
    echo "   curl http://localhost:8080/health"
fi

echo ""
echo -e "${GREEN}📚 Документация: /opt/docagent/README.md${NC}"
echo -e "${GREEN}📊 Логи: /opt/docagent/logs/${NC}"
echo -e "${GREEN}💾 Данные: /opt/docagent/data/${NC}"
echo ""
echo -e "${YELLOW}⚠️  Не забудьте обновить credentials в .env!${NC}"
echo ""
