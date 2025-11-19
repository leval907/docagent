# API Documentation

Базовый URL: `http://localhost:8000`

## Health Check
- **GET** `/health`
  - Проверяет подключение к DuckDB и ArangoDB.
  - Ответ: `{"duckdb": "ok", "arangodb": "ok"}`

## ETL (Extract, Transform, Load)
- **POST** `/etl/run`
  - Запускает полный процесс обработки данных в фоне.
  - Шаги:
    1. Чтение Excel файлов из `input_files/`.
    2. Нормализация данных (очистка названий, дат).
    3. Импорт в DuckDB (таблица `revenue_raw`).
    4. Построение графа в ArangoDB.
  - Ответ: `{"message": "ETL process started in background"}`

## Аналитика (Revenue)
- **GET** `/revenue/summary`
  - Возвращает сводную таблицу выручки по компаниям.
  - Поля: Компания, Выручка, НДС, Итого.

- **GET** `/revenue/structure`
  - Возвращает структуру выручки по типам бухгалтерских проводок (Дт/Кт).

## Граф (Graph)
- **POST** `/graph/build`
  - Принудительный перезапуск построения графа из текущих данных DuckDB.
  
- **GET** `/graph/stats`
  - Статистика графа.
  - Ответ: `{"companies": 150, "transactions": 300}`
