# Setup script for DocAgent (Windows PowerShell)
# Запуск: .\setup.ps1

Write-Host "🚀 DocAgent Setup Script" -ForegroundColor Cyan
Write-Host "=" * 60

# Проверить Python
Write-Host "`n1️⃣ Checking Python..." -ForegroundColor Yellow
if (Get-Command python -ErrorAction SilentlyContinue) {
    $pythonVersion = python --version
    Write-Host "   ✅ Found: $pythonVersion" -ForegroundColor Green
} else {
    Write-Host "   ❌ Python not found! Please install Python 3.11+" -ForegroundColor Red
    exit 1
}

# Создать виртуальное окружение
Write-Host "`n2️⃣ Creating virtual environment..." -ForegroundColor Yellow
if (Test-Path "venv") {
    Write-Host "   ⚠️  venv already exists, skipping..." -ForegroundColor Yellow
} else {
    python -m venv venv
    Write-Host "   ✅ Virtual environment created" -ForegroundColor Green
}

# Активировать окружение
Write-Host "`n3️⃣ Activating virtual environment..." -ForegroundColor Yellow
& .\venv\Scripts\Activate.ps1
Write-Host "   ✅ Environment activated" -ForegroundColor Green

# Установить зависимости
Write-Host "`n4️⃣ Installing dependencies..." -ForegroundColor Yellow
python -m pip install --upgrade pip
pip install -r requirements.txt
Write-Host "   ✅ Dependencies installed" -ForegroundColor Green

# Установить браузеры Playwright
Write-Host "`n5️⃣ Installing Playwright browsers..." -ForegroundColor Yellow
playwright install
Write-Host "   ✅ Playwright browsers installed" -ForegroundColor Green

# Создать директории
Write-Host "`n6️⃣ Creating directories..." -ForegroundColor Yellow
@("logs", "knowledge_base") | ForEach-Object {
    if (!(Test-Path $_)) {
        New-Item -ItemType Directory -Path $_ | Out-Null
    }
}
Write-Host "   ✅ Directories created" -ForegroundColor Green

# Готово
Write-Host "`n" + "=" * 60 -ForegroundColor Cyan
Write-Host "✅ Setup complete!" -ForegroundColor Green
Write-Host "`nNext steps:" -ForegroundColor Cyan
Write-Host "  1. Edit config/sources.yaml to add your documentation sources"
Write-Host "  2. Run: python scripts\crawler_crawl4ai.py --app nocodb"
Write-Host "  3. Build index: python scripts\build_index.py --app nocodb"
Write-Host "`nTo activate environment later, run:" -ForegroundColor Yellow
Write-Host "  .\venv\Scripts\Activate.ps1" -ForegroundColor White
