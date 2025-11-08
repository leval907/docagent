#!/bin/bash
# Setup script for DocAgent (Linux/Mac)
# Запуск: bash setup.sh

echo "🚀 DocAgent Setup Script"
echo "============================================================"

# Проверить Python
echo -e "\n1️⃣ Checking Python..."
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version)
    echo "   ✅ Found: $PYTHON_VERSION"
    PYTHON_CMD=python3
elif command -v python &> /dev/null; then
    PYTHON_VERSION=$(python --version)
    echo "   ✅ Found: $PYTHON_VERSION"
    PYTHON_CMD=python
else
    echo "   ❌ Python not found! Please install Python 3.11+"
    exit 1
fi

# Создать виртуальное окружение
echo -e "\n2️⃣ Creating virtual environment..."
if [ -d "venv" ]; then
    echo "   ⚠️  venv already exists, skipping..."
else
    $PYTHON_CMD -m venv venv
    echo "   ✅ Virtual environment created"
fi

# Активировать окружение
echo -e "\n3️⃣ Activating virtual environment..."
source venv/bin/activate
echo "   ✅ Environment activated"

# Установить зависимости
echo -e "\n4️⃣ Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt
echo "   ✅ Dependencies installed"

# Установить браузеры Playwright
echo -e "\n5️⃣ Installing Playwright browsers..."
playwright install
echo "   ✅ Playwright browsers installed"

# Создать директории
echo -e "\n6️⃣ Creating directories..."
mkdir -p logs knowledge_base
echo "   ✅ Directories created"

# Готово
echo -e "\n============================================================"
echo "✅ Setup complete!"
echo -e "\nNext steps:"
echo "  1. Edit config/sources.yaml to add your documentation sources"
echo "  2. Run: python scripts/crawler_crawl4ai.py --app nocodb"
echo "  3. Build index: python scripts/build_index.py --app nocodb"
echo -e "\nTo activate environment later, run:"
echo "  source venv/bin/activate"
