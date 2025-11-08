# Быстрый запуск краулера с настройками Beget S3 (Windows)

param(
    [string]$App = "openspg",
    [string]$S3Bucket = "db6a1f644d97-la-ducem1",
    [string]$S3Endpoint = "https://s3.ru1.storage.beget.cloud"
)

Write-Host "🚀 Запуск краулера..." -ForegroundColor Green
Write-Host "📱 App: $App"
Write-Host "🪣 S3 Bucket: $S3Bucket"
Write-Host "🌐 S3 Endpoint: $S3Endpoint"
Write-Host ""

# Установка переменных окружения
$env:AWS_ACCESS_KEY_ID = "JQDHVXZY7XFWUHF8LV0S"
$env:AWS_SECRET_ACCESS_KEY = "pjVG1Zt5G6y8N8eYAmPnKcnnPpfxB3KVCcFrEyfk"
$env:PYTHONIOENCODING = "utf-8"

# Путь к Python в виртуальном окружении
$pythonPath = "D:\docs\.venv\Scripts\python.exe"

# Проверка существования Python
if (-not (Test-Path $pythonPath)) {
    Write-Host "❌ Python не найден в виртуальном окружении!" -ForegroundColor Red
    Write-Host "Путь: $pythonPath"
    exit 1
}

# Переход в директорию проекта
Set-Location "D:\docs\DocAgent"

# Запуск краулера
& $pythonPath scripts/crawl_and_clean.py `
    --app $App `
    --s3-bucket $S3Bucket `
    --s3-endpoint $S3Endpoint

Write-Host ""
Write-Host "✅ Готово!" -ForegroundColor Green
