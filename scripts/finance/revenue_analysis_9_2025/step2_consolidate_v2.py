#!/usr/bin/env python3
"""
Шаг 2: Консолидация выручки и анализ внутригрупповых оборотов
Версия 2: работает с DuckDB, использует расшифровку полей
"""

import duckdb
import pandas as pd
from pathlib import Path
import xlsxwriter

# === Настройки ===
OUTPUT_FOLDER = Path("/opt/docagent/data/osv_revenue_0925/output")
DB_PATH = Path("/opt/docagent/knowledge_base/duckdb/osv/osv_database.duckdb")


def analyze_revenue_structure(conn):
    """Анализ структуры выручки по проводкам"""
    print("\n📊 Анализ структуры выручки (расшифровка проводок):")
    print("="*80)
    
    # Получаем список доступных колонок
    columns = [row[0] for row in conn.execute("DESCRIBE revenue_raw").fetchall()]
    
    # Дт 62 Кт 90 - основная деятельность
    if "62_90" in columns:
        query_90 = """
        SELECT 
            SUM(COALESCE("62_90", 0)) as total_90,
            COUNT(*) as doc_count
        FROM revenue_raw
        WHERE COALESCE("62_90", 0) > 0
        """
        result_90 = conn.execute(query_90).fetchone()
        
        print(f"\n📌 Дт62 Кт90 (основная деятельность):")
        print(f"   Отгрузка товаров/оказание услуг")
        print(f"   Сумма: {result_90[0]:>20,.2f} руб.")
        print(f"   Документов: {result_90[1]}")
    else:
        result_90 = (0, 0)
    
    # Дт 62 Кт 91 - прочие доходы
    if "62_91" in columns:
        query_91 = """
        SELECT 
            SUM(COALESCE("62_91", 0)) as total_91,
            COUNT(*) as doc_count
        FROM revenue_raw
        WHERE COALESCE("62_91", 0) > 0
        """
        result_91 = conn.execute(query_91).fetchone()
        
        print(f"\n📌 Дт62 Кт91 (прочие доходы):")
        print(f"   - Продажа внеоборотных активов")
        print(f"   - Продажа материалов/запасов")
        print(f"   - Списание кредиторской задолженности")
        print(f"   - Арендные платежи")
        print(f"   Сумма: {result_91[0]:>20,.2f} руб.")
        print(f"   Документов: {result_91[1]}")
    else:
        result_91 = (0, 0)
    
    # Дт 51 Кт 62 - оплата
    if "51_62" in columns:
        query_51 = """
        SELECT 
            SUM(COALESCE("51_62", 0)) as total_51,
            COUNT(*) as doc_count
        FROM revenue_raw
        WHERE COALESCE("51_62", 0) > 0
        """
        result_51 = conn.execute(query_51).fetchone()
        
        print(f"\n📌 Дт51 Кт62 (оплата от покупателей):")
        print(f"   Поступление на расчетный счет")
        print(f"   Сумма: {result_51[0]:>20,.2f} руб.")
        print(f"   Документов: {result_51[1]}")
    else:
        result_51 = (0, 0)
    
    # Д60 Кт62 - взаимозачет
    if "60_62" in columns:
        query_60 = """
        SELECT 
            SUM(COALESCE("60_62", 0)) as total_60,
            COUNT(*) as doc_count
        FROM revenue_raw
        WHERE COALESCE("60_62", 0) > 0
        """
        result_60 = conn.execute(query_60).fetchone()
        
        if result_60[1] > 0:
            print(f"\n📌 Д60 К62 (взаимозачет):")
            print(f"   Погашение задолженности поставщику")
            print(f"   Сумма: {result_60[0]:>20,.2f} руб.")
            print(f"   Документов: {result_60[1]}")
    else:
        result_60 = (0, 0)
    
    # Дт62 Кт51 - возврат аванса
    if "62_51" in columns:
        query_62_51 = """
        SELECT 
            SUM(COALESCE("62_51", 0)) as total,
            COUNT(*) as doc_count
        FROM revenue_raw
        WHERE COALESCE("62_51", 0) > 0
        """
        result_62_51 = conn.execute(query_62_51).fetchone()
        
        if result_62_51[1] > 0:
            print(f"\n📌 Дт62 Кт51 (возврат аванса покупателю):")
            print(f"   Корректировка расчетов/возврат")
            print(f"   Сумма: {result_62_51[0]:>20,.2f} руб.")
            print(f"   Документов: {result_62_51[1]}")
    
    # Дт76 Кт62 - расчёты с разными дебиторами
    if "76_62" in columns:
        query_76 = """
        SELECT 
            SUM(COALESCE("76_62", 0)) as total,
            COUNT(*) as doc_count
        FROM revenue_raw
        WHERE COALESCE("76_62", 0) > 0
        """
        result_76 = conn.execute(query_76).fetchone()
        
        if result_76[1] > 0:
            print(f"\n📌 Дт76 Кт62 (расчёты с разными дебиторами):")
            print(f"   Погашение задолженности покупателя через счёт 76")
            print(f"   Сумма: {result_76[0]:>20,.2f} руб.")
            print(f"   Документов: {result_76[1]}")
    
    total_revenue = result_90[0] + result_91[0]
    print(f"\n{'─'*80}")
    print(f"💰 ИТОГО начислено (90+91): {total_revenue:>20,.2f} руб.")
    if result_51[0] > 0:
        print(f"💵 Оплачено (51):           {result_51[0]:>20,.2f} руб.")
        payment_rate = (result_51[0] / total_revenue * 100) if total_revenue > 0 else 0
        print(f"📊 Процент оплаты:          {payment_rate:>20.1f}%")
    print("="*80)


def consolidate_revenue():
    """Основная функция консолидации выручки"""
    print("="*80)
    print("📊 Шаг 2: Консолидация выручки группы (9 месяцев 2025)")
    print("="*80)
    
    if not DB_PATH.exists():
        print(f"\n❌ База данных не найдена: {DB_PATH}")
        print("   Сначала запустите step1_normalize_v2.py")
        return
    
    OUTPUT_FOLDER.mkdir(parents=True, exist_ok=True)

    # Подключаемся к DuckDB
    conn = duckdb.connect(str(DB_PATH))
    
    # Проверяем наличие таблиц
    tables = conn.execute("SHOW TABLES").fetchall()
    table_names = [t[0] for t in tables]
    
    if 'revenue_raw' not in table_names:
        print(f"\n❌ Таблица revenue_raw не найдена в базе данных")
        print("   Сначала запустите step1_normalize_v2.py")
        conn.close()
        return
    
    if 'group_companies' not in table_names:
        print(f"\n⚠️  Таблица group_companies не найдена")
        print("   Продолжаем без определения внутригрупповых транзакций")
        group_companies = []
    else:
        # Загружаем список компаний группы
        group_companies = conn.execute("SELECT company_name FROM group_companies").fetchdf()['company_name'].tolist()
        print(f"\n📋 Загружено {len(group_companies)} компаний группы")
    
    # Анализ структуры выручки
    analyze_revenue_structure(conn)

    print("\n🔍 Консолидация выручки по компаниям...")

    # Получаем список доступных колонок
    columns = [row[0] for row in conn.execute("DESCRIBE revenue_raw").fetchall()]
    
    # Создаем условия для проверки внутригрупповых транзакций
    if group_companies:
        like_conditions = ' OR '.join([
            f"UPPER(\"Контрагент\") LIKE '%{comp.upper()}%'" 
            for comp in group_companies
        ])
    else:
        like_conditions = "FALSE"

    # Формируем SELECT для доступных колонок
    select_parts = []
    select_parts.append('COALESCE("Начальное сальдо Дт", 0) as начальное_сальдо_дт' if "Начальное сальдо Дт" in columns else '0 as начальное_сальдо_дт')
    select_parts.append('COALESCE("Начальное сальдо Кт", 0) as начальное_сальдо_кт' if "Начальное сальдо Кт" in columns else '0 as начальное_сальдо_кт')
    select_parts.append('COALESCE("62_90", 0) as счет_90' if "62_90" in columns else '0 as счет_90')
    select_parts.append('COALESCE("62_91", 0) as счет_91' if "62_91" in columns else '0 as счет_91')
    select_parts.append('COALESCE("51_62", 0) as оплата_51' if "51_62" in columns else '0 as оплата_51')
    select_parts.append('COALESCE("60_62", 0) as взаимозачет_60' if "60_62" in columns else '0 as взаимозачет_60')
    select_parts.append('COALESCE("76_62", 0) as оплата_76' if "76_62" in columns else '0 as оплата_76')
    select_parts.append('COALESCE("62_51", 0) as возврат_62_51' if "62_51" in columns else '0 as возврат_62_51')
    select_parts.append('COALESCE("Конечное сальдо Дт", 0) as конечное_сальдо_дт' if "Конечное сальдо Дт" in columns else '0 as конечное_сальдо_дт')
    select_parts.append('COALESCE("Конечное сальдо Кт", 0) as конечное_сальдо_кт' if "Конечное сальдо Кт" in columns else '0 as конечное_сальдо_кт')

    # SQL запрос для консолидации выручки
    query = f"""
    WITH revenue_transactions AS (
        SELECT
            "Компания",
            "Контрагент",
            "Документ",
            {', '.join(select_parts)},
            COALESCE("62_90", 0) + COALESCE("62_91", 0) as выручка_начислено,
            -- Определяем внутригрупповую транзакцию
            CASE
                WHEN {like_conditions}
                THEN TRUE
                ELSE FALSE
            END as внутригрупповая
        FROM revenue_raw
        WHERE (COALESCE("62_90", 0) > 0 OR COALESCE("62_91", 0) > 0)
    )
    SELECT
        "Компания",
        SUM(начальное_сальдо_дт) as начальное_сальдо_дт,
        SUM(начальное_сальдо_кт) as начальное_сальдо_кт,
        SUM(выручка_начислено) as выручка_всего,
        SUM(CASE WHEN внутригрупповая THEN выручка_начислено ELSE 0 END) as внутригрупповая_выручка,
        SUM(CASE WHEN NOT внутригрупповая THEN выручка_начислено ELSE 0 END) as внешняя_выручка,
        SUM(счет_90) as счет_90_основная,
        SUM(счет_91) as счет_91_прочие,
        SUM(оплата_51) as оплачено_51,
        SUM(взаимозачет_60) as взаимозачет_60,
        SUM(оплата_76) as оплачено_76,
        SUM(возврат_62_51) as возврат_аванса,
        SUM(конечное_сальдо_дт) as конечное_сальдо_дт,
        SUM(конечное_сальдо_кт) as конечное_сальдо_кт,
        COUNT(*) as документов
    FROM revenue_transactions
    GROUP BY "Компания"
    ORDER BY "Компания";
    """

    # Выполняем запрос
    result_df = conn.execute(query).df()

    # Запрос для детальной таблицы выручки
    detail_select_parts = []
    detail_select_parts.append('COALESCE("Начальное сальдо Дт", 0) as начальное_сальдо_дт' if "Начальное сальдо Дт" in columns else '0 as начальное_сальдо_дт')
    detail_select_parts.append('COALESCE("Начальное сальдо Кт", 0) as начальное_сальдо_кт' if "Начальное сальдо Кт" in columns else '0 as начальное_сальдо_кт')
    detail_select_parts.append('COALESCE("62_90", 0) as счет_90_основная' if "62_90" in columns else '0 as счет_90_основная')
    detail_select_parts.append('COALESCE("62_91", 0) as счет_91_прочие' if "62_91" in columns else '0 as счет_91_прочие')
    detail_select_parts.append('COALESCE("51_62", 0) as оплачено_51' if "51_62" in columns else '0 as оплачено_51')
    detail_select_parts.append('COALESCE("60_62", 0) as взаимозачет_60' if "60_62" in columns else '0 as взаимозачет_60')
    detail_select_parts.append('COALESCE("76_62", 0) as оплачено_76' if "76_62" in columns else '0 as оплачено_76')
    detail_select_parts.append('COALESCE("Конечное сальдо Дт", 0) as конечное_сальдо_дт' if "Конечное сальдо Дт" in columns else '0 as конечное_сальдо_дт')
    detail_select_parts.append('COALESCE("Конечное сальдо Кт", 0) as конечное_сальдо_кт' if "Конечное сальдо Кт" in columns else '0 as конечное_сальдо_кт')
    
    detail_query = f"""
    SELECT
        "Компания",
        "Контрагент",
        "Документ",
        {', '.join(detail_select_parts)},
        COALESCE("62_90", 0) + COALESCE("62_91", 0) as выручка_начислено,
        -- Определяем тип контрагента
        CASE
            WHEN {like_conditions}
            THEN 'Внутригрупповая'
            ELSE 'Внешняя'
        END as тип_контрагента
    FROM revenue_raw
    WHERE (COALESCE("62_90", 0) > 0 OR COALESCE("62_91", 0) > 0)
    ORDER BY "Компания", тип_контрагента, "Контрагент", "Документ";
    """
    
    detail_df = conn.execute(detail_query).df()
    
    # Отдельные таблицы для внешней и внутригрупповой выручки
    external_df = detail_df[detail_df['тип_контрагента'] == 'Внешняя'].copy()
    internal_df = detail_df[detail_df['тип_контрагента'] == 'Внутригрупповая'].copy()
    
    external_df = external_df.drop(columns=['тип_контрагента'])
    internal_df = internal_df.drop(columns=['тип_контрагента'])

    # Добавляем итоговую строку
    totals = pd.DataFrame([{
        'Компания': 'ИТОГО ПО ГРУППЕ',
        'начальное_сальдо_дт': result_df['начальное_сальдо_дт'].sum(),
        'начальное_сальдо_кт': result_df['начальное_сальдо_кт'].sum(),
        'выручка_всего': result_df['выручка_всего'].sum(),
        'внутригрупповая_выручка': result_df['внутригрупповая_выручка'].sum(),
        'внешняя_выручка': result_df['внешняя_выручка'].sum(),
        'счет_90_основная': result_df['счет_90_основная'].sum(),
        'счет_91_прочие': result_df['счет_91_прочие'].sum(),
        'оплачено_51': result_df['оплачено_51'].sum(),
        'взаимозачет_60': result_df['взаимозачет_60'].sum(),
        'оплачено_76': result_df['оплачено_76'].sum(),
        'возврат_аванса': result_df['возврат_аванса'].sum(),
        'конечное_сальдо_дт': result_df['конечное_сальдо_дт'].sum(),
        'конечное_сальдо_кт': result_df['конечное_сальдо_кт'].sum(),
        'документов': result_df['документов'].sum()
    }])
    result_with_totals = pd.concat([result_df, totals], ignore_index=True)

    # Сохраняем результаты
    output_file = OUTPUT_FOLDER / "consolidated_revenue.xlsx"

    # === Файл: Консолидация с несколькими листами ===
    with pd.ExcelWriter(output_file, engine='xlsxwriter') as writer:
        # Лист 1: Консолидация по компаниям
        result_with_totals.to_excel(writer, index=False, sheet_name='Консолидация')
        
        # Лист 2: Детали внешней выручки
        external_df.to_excel(writer, index=False, sheet_name='Внешняя выручка')
        
        # Лист 3: Детали внутригрупповой выручки
        if len(internal_df) > 0:
            internal_df.to_excel(writer, index=False, sheet_name='Внутригрупповая')

        workbook = writer.book
        
        # Форматы
        header_format = workbook.add_format({
            'bold': True,
            'bg_color': '#4472C4',
            'font_color': 'white',
            'border': 1,
            'align': 'center',
            'valign': 'vcenter'
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
        
        # === Форматирование листа "Консолидация" ===
        worksheet = writer.sheets['Консолидация']
        
        # Заголовки
        for col_num, value in enumerate(result_with_totals.columns.values):
            worksheet.write(0, col_num, value, header_format)

        # Данные
        for row_num in range(1, len(result_with_totals)):
            worksheet.write(row_num, 0, result_with_totals.iloc[row_num-1, 0])
            for col_num in range(1, len(result_with_totals.columns)):
                worksheet.write(row_num, col_num, 
                              result_with_totals.iloc[row_num-1, col_num], 
                              money_format)

        # Итоговая строка
        total_row = len(result_with_totals)
        worksheet.write(total_row, 0, result_with_totals.iloc[-1, 0], total_format)
        for col_num in range(1, len(result_with_totals.columns)):
            worksheet.write(total_row, col_num, 
                          result_with_totals.iloc[-1, col_num], 
                          total_format)

        worksheet.set_column('A:A', 25)
        worksheet.set_column('B:P', 18)  # Все числовые колонки (добавлена колонка 76_62)
        
        # === Форматирование листа "Внешняя выручка" ===
        worksheet2 = writer.sheets['Внешняя выручка']
        
        header_format2 = workbook.add_format({
            'bold': True,
            'bg_color': '#70AD47',
            'font_color': 'white',
            'border': 1,
            'align': 'center'
        })
        
        for col_num, value in enumerate(external_df.columns.values):
            worksheet2.write(0, col_num, value, header_format2)

        for row_num in range(1, len(external_df) + 1):
            for col_num in range(3):
                worksheet2.write(row_num, col_num, external_df.iloc[row_num-1, col_num])
            for col_num in range(3, len(external_df.columns)):
                worksheet2.write(row_num, col_num, 
                              external_df.iloc[row_num-1, col_num], 
                              money_format)

        worksheet2.set_column('A:A', 25)
        worksheet2.set_column('B:B', 40)
        worksheet2.set_column('C:C', 50)
        worksheet2.set_column('D:L', 16)  # Числовые колонки
        
        # === Форматирование листа "Внутригрупповая" ===
        if len(internal_df) > 0:
            worksheet3 = writer.sheets['Внутригрупповая']
            
            header_format3 = workbook.add_format({
                'bold': True,
                'bg_color': '#FFC000',
                'font_color': 'white',
                'border': 1,
                'align': 'center'
            })
            
            for col_num, value in enumerate(internal_df.columns.values):
                worksheet3.write(0, col_num, value, header_format3)

            for row_num in range(1, len(internal_df) + 1):
                for col_num in range(3):
                    worksheet3.write(row_num, col_num, internal_df.iloc[row_num-1, col_num])
                for col_num in range(3, len(internal_df.columns)):
                    worksheet3.write(row_num, col_num, 
                                  internal_df.iloc[row_num-1, col_num], 
                                  money_format)

            worksheet3.set_column('A:A', 25)
            worksheet3.set_column('B:B', 40)
            worksheet3.set_column('C:C', 50)
            worksheet3.set_column('D:L', 16)  # Числовые колонки

    print("\n" + "="*80)
    print(f"💾 Результаты сохранены: {output_file}")
    print(f"   📄 Лист 'Консолидация': {len(result_df)} компаний")
    print(f"   📄 Лист 'Внешняя выручка': {len(external_df)} документов")
    if len(internal_df) > 0:
        print(f"   📄 Лист 'Внутригрупповая': {len(internal_df)} документов")
    print("="*80)
    
    print("\n📊 Консолидированная выручка по компаниям:")
    print(result_df[['Компания', 'начальное_сальдо_дт', 'выручка_всего', 'внешняя_выручка', 'конечное_сальдо_дт', 'документов']].to_string(index=False))
    
    print("\n" + "="*80)
    print("💰 ИТОГО ПО ГРУППЕ за 9 месяцев 2025:")
    print("="*80)
    print(f"  Остаток на начало (Дт):       {result_df['начальное_сальдо_дт'].sum():>20,.2f} руб.")
    print(f"  Остаток на начало (Кт):       {result_df['начальное_сальдо_кт'].sum():>20,.2f} руб.")
    print(f"\n  Выручка всего (начислено):    {result_df['выручка_всего'].sum():>20,.2f} руб.")
    print(f"    - Счет 90 (основная):        {result_df['счет_90_основная'].sum():>20,.2f} руб.")
    print(f"    - Счет 91 (прочие доходы):   {result_df['счет_91_прочие'].sum():>20,.2f} руб.")
    print(f"\n  Внутригрупповые обороты:      {result_df['внутригрупповая_выручка'].sum():>20,.2f} руб.")
    print(f"  {'─'*60}")
    print(f"  ВНЕШНЯЯ ВЫРУЧКА (чистая):     {result_df['внешняя_выручка'].sum():>20,.2f} руб.")
    print(f"\n  Оплачено (Д51 К62):           {result_df['оплачено_51'].sum():>20,.2f} руб.")
    if result_df['взаимозачет_60'].sum() > 0:
        print(f"  Взаимозачет (Д60 К62):        {result_df['взаимозачет_60'].sum():>20,.2f} руб.")
    if result_df['возврат_аванса'].sum() > 0:
        print(f"  Возврат аванса (Д62 К51):     {result_df['возврат_аванса'].sum():>20,.2f} руб.")
    print(f"\n  Остаток на конец (Дт):        {result_df['конечное_сальдо_дт'].sum():>20,.2f} руб.")
    print(f"  Остаток на конец (Кт):        {result_df['конечное_сальдо_кт'].sum():>20,.2f} руб.")
    print(f"\n  Документов обработано:        {result_df['документов'].sum()}")
    print("="*80)

    # Закрываем соединение
    conn.close()

    return result_df


if __name__ == "__main__":
    consolidate_revenue()
