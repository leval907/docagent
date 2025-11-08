#!/bin/bash
# Быстрый запуск краулера с настройками Beget S3

# Проверка виртуального окружения
if [ ! -d "venv" ]; then
    echo "❌ Виртуальное окружение не найдено!"
    echo "Запустите сначала: ./install.sh"
    exit 1
fi

# Активация окружения
source venv/bin/activate

# Экспорт переменных для S3
export AWS_ACCESS_KEY_ID="${AWS_ACCESS_KEY_ID:-JQDHVXZY7XFWUHF8LV0S}"
export AWS_SECRET_ACCESS_KEY="${AWS_SECRET_ACCESS_KEY:-pjVG1Zt5G6y8N8eYAmPnKcnnPpfxB3KVCcFrEyfk}"
export PYTHONIOENCODING=utf-8

# Параметры по умолчанию
APP="${1:-openspg}"
S3_BUCKET="${S3_BUCKET:-db6a1f644d97-la-ducem1}"
S3_ENDPOINT="${S3_ENDPOINT:-https://s3.ru1.storage.beget.cloud}"

echo "🚀 Запуск краулера..."
echo "📱 App: $APP"
echo "🪣 S3 Bucket: $S3_BUCKET"
echo "🌐 S3 Endpoint: $S3_ENDPOINT"
echo ""

# Запуск
python scripts/crawl_and_clean.py \
    --app "$APP" \
    --s3-bucket "$S3_BUCKET" \
    --s3-endpoint "$S3_ENDPOINT"

echo ""
echo "✅ Готово!"
