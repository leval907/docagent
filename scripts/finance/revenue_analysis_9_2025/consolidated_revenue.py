#!/usr/bin/env python3
"""
Шаг 2: Консолидация выручки и анализ внутригрупповых оборотов
Использует нормализованную таблицу из step1_normalize.py
"""

import duckdb
import pandas as pd
from pathlib import Path
import xlsxwriter

# === Настройки ===
NORMALIZED_FILE = Path("/opt/docagent/data/osv_revenue_0925/output/normalized_osv.xlsx")
OUTPUT_FOLDER = Path("/opt/docagent/data/osv_revenue_0925/output")
DB_PATH = Path("/opt/docagent/knowledge_base/duckdb/osv/osv_database.duckdb")

# Список всех компаний группы (16 штук)
# Добавлены полные названия для точного сопоставления
GROUP_COMPANIES = [
    "Альянс", "АЛЬЯНС ООО",
    "Бос", "БОС ООО",
    "ВФЦ", "ВФЦ ООО",
    "Вайтера", "ВАЙТЕРА ООО",
    "Владение-В", "ВЛАДЕНИЕ-В ООО",
    "ГГДИ", "ГРОСС ГРУП ДИ ООО",
    "ГГМ", "ГРОСС ГРУП М ООО",
    "Грандпром", "ГРАНДПРОМ АО",
    "Джул Лайф", "ДЖУЛ ЛАЙФ ООО",
    "К-Строй", "К-СТРОЙ АО",
    "Монолит", "МОНОЛИТ ООО",
    "СГК-Регион", "СГК-РЕГИОН ООО",
    "УК Гросс", "УК ГРОСС ООО",
    "Фетер", "ФЕТЕР ООО",
    "Шиндяпин", "ШИНДЯПИН ООО",
    "Юг-Истейт", "ЮГ ИСТЕЙТ", "ЮГ-ИСТЕЙТ", "ЮГ ИСТЕЙТ ИНЖИНИРИНГ ООО"
]


def load_normalized_to_duckdb(conn):
    """Загружает нормализованную таблицу в DuckDB"""
    print("📊 Загрузка нормализованных данных в DuckDB...")
    
    if not NORMALIZED_FILE.exists():
        raise FileNotFoundError(f"Файл не найден: {NORMALIZED_FILE}\nСначала запустите step1_normalize.py")
    
    # Читаем нормализованную таблицу
    df = pd.read_excel(NORMALIZED_FILE, engine='openpyxl')
    
    print(f"  ✅ Загружено: {len(df)} документов")
    print(f"  📋 Компаний: {df['Компания'].nunique()}")
    print(f"  👥 Контрагентов: {df['Контрагент'].nunique()}")
    
    # Создаем таблицу в DuckDB
    conn.execute("DROP TABLE IF EXISTS revenue_raw;")
    conn.execute("CREATE TABLE revenue_raw AS SELECT * FROM df")
    
    return len(df)


def consolidate_revenue():
    """Основная функция консолидации выручки"""
    print("="*80)
    print("📊 Шаг 2: Консолидация выручки группы (9 месяцев 2025)")
    print("="*80)
    
    OUTPUT_FOLDER.mkdir(parents=True, exist_ok=True)
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    # Подключаемся к DuckDB
    conn = duckdb.connect(str(DB_PATH))

    # Загружаем нормализованные данные
    load_normalized_to_duckdb(conn)

    print("\n🔍 Анализ выручки и внутригрупповых оборотов...")

    # Создаем условия для проверки внутригрупповых транзакций
    # Проверяем, содержит ли поле "Контрагент" название компании из группы
    like_conditions = ' OR '.join([
        f"LOWER(\"Контрагент\") LIKE '%{comp.lower()}%'" 
        for comp in GROUP_COMPANIES
    ])

    # SQL запрос для консолидации выручки
    # Учитываем счета 90 (основная выручка) и 91 (прочие доходы)
    query = f"""
    WITH revenue_transactions AS (
        SELECT
            "Компания",
            "Контрагент",
            "Документ",
            COALESCE("90", 0) + COALESCE("91", 0) as выручка_начислено,
            "90" as счет_90,
            "91" as счет_91,
            "51" as оплата,
            -- Определяем внутригрупповую транзакцию
            CASE
                WHEN {like_conditions}
                THEN TRUE
                ELSE FALSE
            END as внутригрупповая
        FROM revenue_raw
        WHERE (COALESCE("90", 0) > 0 OR COALESCE("91", 0) > 0)
    )
    SELECT
        "Компания",
        SUM(выручка_начислено) as выручка_всего,
        SUM(CASE WHEN внутригрупповая THEN выручка_начислено ELSE 0 END) as внутригрупповая,
        SUM(CASE WHEN NOT внутригрупповая THEN выручка_начислено ELSE 0 END) as внешняя_выручка,
        SUM(счет_90) as выручка_90,
        SUM(счет_91) as прочие_доходы_91,
        SUM(оплата) as оплачено_51
    FROM revenue_transactions
    GROUP BY "Компания"
    ORDER BY "Компания";
    """

    # Выполняем запрос
    result_df = conn.execute(query).df()

    # Запрос для детальной таблицы внешней выручки
    detail_query = f"""
    SELECT
        "Компания",
        "Контрагент",
        "Документ",
        COALESCE("Начальное сальдо Дт", 0) as начальное_сальдо,
        COALESCE("90", 0) as счет_90,
        COALESCE("91", 0) as счет_91,
        COALESCE("90", 0) + COALESCE("91", 0) as выручка_начислено,
        COALESCE("51", 0) as оплачено,
        COALESCE("Конечное сальдо Дт", 0) as конечное_сальдо,
        -- Определяем внутригрупповую транзакцию
        CASE
            WHEN {like_conditions}
            THEN 'Внутригрупповая'
            ELSE 'Внешняя'
        END as тип_контрагента
    FROM revenue_raw
    WHERE (COALESCE("90", 0) > 0 OR COALESCE("91", 0) > 0)
    ORDER BY "Компания", "Контрагент", "Документ";
    """
    
    detail_df = conn.execute(detail_query).df()
    
    # Фильтруем только внешнюю выручку
    external_df = detail_df[detail_df['тип_контрагента'] == 'Внешняя'].copy()
    external_df = external_df.drop(columns=['тип_контрагента'])

    # Добавляем итоговую строку
    totals = pd.DataFrame([{
        'Компания': 'ИТОГО ПО ГРУППЕ',
        'выручка_всего': result_df['выручка_всего'].sum(),
        'внутригрупповая': result_df['внутригрупповая'].sum(),
        'внешняя_выручка': result_df['внешняя_выручка'].sum(),
        'выручка_90': result_df['выручка_90'].sum(),
        'прочие_доходы_91': result_df['прочие_доходы_91'].sum(),
        'оплачено_51': result_df['оплачено_51'].sum()
    }])
    result_with_totals = pd.concat([result_df, totals], ignore_index=True)

    # Сохраняем результат с форматированием
    output_file = OUTPUT_FOLDER / "consolidated_revenue.xlsx"
    external_file = OUTPUT_FOLDER / "external_revenue_detail.xlsx"

    # === Файл 1: Консолидация по компаниям ===
    with pd.ExcelWriter(output_file, engine='xlsxwriter') as writer:
        result_with_totals.to_excel(writer, index=False, sheet_name='Консолидация')

        workbook = writer.book
        worksheet = writer.sheets['Консолидация']

        # Форматы
        header_format = workbook.add_format({
            'bold': True,
            'bg_color': '#4472C4',
            'font_color': 'white',
            'border': 1,
            'align': 'center'
        })

        money_format = workbook.add_format({
            'num_format': '#,##0.00',
            'border': 1
        })

        total_format = workbook.add_format({
            'num_format': '#,##0.00',
            'border': 1,
            'bold': True,
            'bg_color': '#FFF2CC'
        })

        # Применяем форматы для заголовков
        for col_num, value in enumerate(result_with_totals.columns.values):
            worksheet.write(0, col_num, value, header_format)

        # Форматируем данные
        for row_num in range(1, len(result_with_totals)):
            # Компания
            worksheet.write(row_num, 0, result_with_totals.iloc[row_num-1, 0])
            # Числовые колонки
            for col_num in range(1, len(result_with_totals.columns)):
                worksheet.write(row_num, col_num, 
                              result_with_totals.iloc[row_num-1, col_num], 
                              money_format)

        # Итоговая строка с выделением
        total_row = len(result_with_totals)
        worksheet.write(total_row, 0, result_with_totals.iloc[-1, 0], total_format)
        for col_num in range(1, len(result_with_totals.columns)):
            worksheet.write(total_row, col_num, 
                          result_with_totals.iloc[-1, col_num], 
                          total_format)

        # Настраиваем ширину колонок
        worksheet.set_column('A:A', 20)  # Компания
        worksheet.set_column('B:G', 18)  # Числовые колонки

    # === Файл 2: Детальная таблица внешней выручки ===
    with pd.ExcelWriter(external_file, engine='xlsxwriter') as writer:
        external_df.to_excel(writer, index=False, sheet_name='Внешняя выручка')

        workbook = writer.book
        worksheet = writer.sheets['Внешняя выручка']

        # Форматы
        header_format = workbook.add_format({
            'bold': True,
            'bg_color': '#70AD47',
            'font_color': 'white',
            'border': 1,
            'align': 'center'
        })

        money_format = workbook.add_format({
            'num_format': '#,##0.00',
            'border': 1
        })

        # Применяем форматы для заголовков
        for col_num, value in enumerate(external_df.columns.values):
            worksheet.write(0, col_num, value, header_format)

        # Форматируем данные
        for row_num in range(1, len(external_df) + 1):
            # Компания, Контрагент, Документ
            for col_num in range(3):
                worksheet.write(row_num, col_num, external_df.iloc[row_num-1, col_num])
            # Числовые колонки
            for col_num in range(3, len(external_df.columns)):
                worksheet.write(row_num, col_num, 
                              external_df.iloc[row_num-1, col_num], 
                              money_format)

        # Настраиваем ширину колонок
        worksheet.set_column('A:A', 20)  # Компания
        worksheet.set_column('B:B', 35)  # Контрагент
        worksheet.set_column('C:C', 45)  # Документ
        worksheet.set_column('D:I', 16)  # Числовые колонки

    print("="*80)
    print(f"💾 Результаты сохранены:")
    print(f"   1. Консолидация: {output_file}")
    print(f"   2. Детали внешней выручки: {external_file}")
    print(f"      → {len(external_df)} документов с внешними контрагентами")
    print("="*80)
    print("\n📊 Консолидированная выручка по компаниям:")
    print(result_df[['Компания', 'выручка_всего', 'внутригрупповая', 'внешняя_выручка']].to_string(index=False))
    
    print("\n" + "="*80)
    print("💰 ИТОГО ПО ГРУППЕ за 9 месяцев 2025:")
    print("="*80)
    print(f"  Выручка всего (начислено):  {result_df['выручка_всего'].sum():>20,.2f} руб.")
    print(f"    - Счет 90 (основная):      {result_df['выручка_90'].sum():>20,.2f} руб.")
    print(f"    - Счет 91 (прочие доходы): {result_df['прочие_доходы_91'].sum():>20,.2f} руб.")
    print(f"\n  Внутригрупповые обороты:    {result_df['внутригрупповая'].sum():>20,.2f} руб.")
    print(f"  {'─'*60}")
    print(f"  ВНЕШНЯЯ ВЫРУЧКА (чистая):   {result_df['внешняя_выручка'].sum():>20,.2f} руб.")
    print(f"\n  Оплачено (Д51 К62):         {result_df['оплачено_51'].sum():>20,.2f} руб.")
    print("="*80)

    # Закрываем соединение
    conn.close()

    return result_df

if __name__ == "__main__":
    consolidate_revenue()
