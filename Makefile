# Makefile для DocAgent Parser
# Использование: make <command>

.PHONY: help build up logs clean test

# Переменные
DOCKER_COMPOSE = docker-compose
PYTHON = python

help: ## Показать эту справку
	@echo "📚 DocAgent Parser Commands:"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'
	@echo ""

# ============================================
# Docker команды
# ============================================

build: ## Собрать Docker образ парсера
	$(DOCKER_COMPOSE) build docagent

logs: ## Показать логи
	tail -f logs/*.log

clean-docker: ## Удалить образ и контейнер
	$(DOCKER_COMPOSE) down --rmi all

# ============================================
# Локальные команды (без Docker)
# ============================================

install: ## Установить зависимости
	pip install -r requirements.txt
	@if [ ! -d "tools/markdown-crawler" ]; then \
		mkdir -p tools; \
		cd tools && git clone https://github.com/paulpierre/markdown-crawler.git; \
		cd markdown-crawler && pip install -r requirements.txt; \
	fi

list: ## Список приложений
	$(PYTHON) scripts/wrapper_crawler.py --list

crawl: ## Crawl приложения (пример: make crawl APP=dbgpt)
	$(PYTHON) scripts/wrapper_crawler.py --app $(APP)

crawl-all: ## Crawl всех приложений
	$(PYTHON) scripts/wrapper_crawler.py --all

process: ## Добавить метаданные (пример: make process APP=dbgpt)
	$(PYTHON) scripts/postprocess.py --app $(APP)

process-all: ## Обработать все приложения
	$(PYTHON) scripts/postprocess.py --all

index: ## Создать индекс (пример: make index APP=dbgpt)
	$(PYTHON) scripts/build_index.py --app $(APP)

index-all: ## Создать глобальный индекс
	$(PYTHON) scripts/build_index.py --all

search: ## Поиск (пример: make search QUERY="RAG" APP=dbgpt)
	$(PYTHON) scripts/build_index.py --search "$(QUERY)" --app $(APP)

# ============================================
# Pipeline команды
# ============================================

pipeline: ## Полный pipeline для приложения (make pipeline APP=dbgpt)
	@echo "🚀 Running pipeline for $(APP)..."
	$(PYTHON) scripts/wrapper_crawler.py --app $(APP)
	$(PYTHON) scripts/postprocess.py --app $(APP)
	$(PYTHON) scripts/build_index.py --app $(APP)
	@echo "✅ Pipeline complete!"

pipeline-all: ## Полный pipeline для всех приложений
	@echo "🚀 Running full pipeline..."
	$(PYTHON) scripts/wrapper_crawler.py --all
	$(PYTHON) scripts/postprocess.py --all
	$(PYTHON) scripts/build_index.py --all
	@echo "✅ Full pipeline complete!"

# ============================================
# Docker pipeline команды
# ============================================

docker-crawl: ## Crawl в Docker (make docker-crawl APP=dbgpt)
	$(DOCKER_COMPOSE) run --rm docagent scripts/wrapper_crawler.py --app $(APP)

docker-process: ## Process в Docker
	$(DOCKER_COMPOSE) run --rm docagent scripts/postprocess.py --app $(APP)

docker-index: ## Index в Docker
	$(DOCKER_COMPOSE) run --rm docagent scripts/build_index.py --app $(APP)

docker-pipeline: ## Полный pipeline в Docker (make docker-pipeline APP=dbgpt)
	@echo "🚀 Running Docker pipeline for $(APP)..."
	$(DOCKER_COMPOSE) run --rm docagent scripts/wrapper_crawler.py --app $(APP)
	$(DOCKER_COMPOSE) run --rm docagent scripts/postprocess.py --app $(APP)
	$(DOCKER_COMPOSE) run --rm docagent scripts/build_index.py --app $(APP)
	@echo "✅ Docker pipeline complete!"

# ============================================
# Тестирование
# ============================================

test: ## Запустить тесты
	$(PYTHON) tests/test_crawler.py

docker-test: ## Тесты в Docker
	$(DOCKER_COMPOSE) run --rm docagent tests/test_crawler.py

# ============================================
# Утилиты
# ============================================

clean: ## Очистить временные файлы
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	rm -rf logs/*.log

clean-kb: ## Очистить knowledge_base
	rm -rf knowledge_base/*
	touch knowledge_base/.gitkeep

stats: ## Статистика проекта
	@echo "📊 Project Statistics:"
	@echo "  Knowledge Base:"
	@find knowledge_base -type f -name "*.md" | wc -l | xargs echo "    MD Files:"
	@du -sh knowledge_base 2>/dev/null | awk '{print "    Size: " $$1}' || echo "    Size: 0"
	@echo "  Logs:"
	@find logs -type f 2>/dev/null | wc -l | xargs echo "    Files:" || echo "    Files: 0"
