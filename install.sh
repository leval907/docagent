#!/bin/bash
# Скрипт быстрой установки DocAgent на сервере

set -e  # Остановка при ошибке

echo "🚀 Установка DocAgent..."

# 1. Обновление системы
echo "📦 Обновление пакетов..."
sudo apt-get update
sudo apt-get install -y python3 python3-pip python3-venv git

# 2. Клонирование репозитория
echo "📥 Клонирование репозитория..."
if [ ! -d "docagent" ]; then
    git clone https://github.com/leval907/docagent.git
fi
cd docagent

# 3. Создание виртуального окружения
echo "🔧 Создание виртуального окружения..."
python3 -m venv venv
source venv/bin/activate

# 4. Установка зависимостей
echo "📚 Установка Python зависимостей..."
pip install --upgrade pip
pip install -r requirements.txt

# 5. Установка Playwright
echo "🎭 Установка Playwright браузеров..."
playwright install chromium
playwright install-deps chromium

# 6. Создание конфигурации
echo "⚙️  Создание .env файла..."
if [ ! -f ".env" ]; then
    cp .env.example .env
    echo ""
    echo "❗ ВАЖНО: Отредактируйте файл .env с вашими данными:"
    echo "   nano .env"
    echo ""
fi

# 7. Создание директорий
echo "📁 Создание директорий..."
mkdir -p knowledge_base
mkdir -p logs

# 8. Проверка установки
echo ""
echo "✅ Установка завершена!"
echo ""
echo "📋 Следующие шаги:"
echo "1. Отредактируйте .env файл: nano .env"
echo "2. Добавьте ваши S3 credentials:"
echo "   AWS_ACCESS_KEY_ID=JQDHVXZY7XFWUHF8LV0S"
echo "   AWS_SECRET_ACCESS_KEY=pjVG1Zt5G6y8N8eYAmPnKcnnPpfxB3KVCcFrEyfk"
echo ""
echo "3. Запустите краулер:"
echo "   source venv/bin/activate"
echo "   python scripts/crawl_and_clean.py --app openspg \\"
echo "     --s3-bucket db6a1f644d97-la-ducem1 \\"
echo "     --s3-endpoint https://s3.ru1.storage.beget.cloud"
echo ""
echo "🎉 Готово!"
