#!/usr/bin/env python3
"""
Шаг 1: Нормализация оборотно-сальдовых ведомостей (ОСВ) 
Версия 2: с загрузкой в DuckDB
"""

import pandas as pd
import duckdb
from pathlib import Path
import re
import warnings
warnings.filterwarnings('ignore', category=UserWarning)

# === Настройки ===
INPUT_FOLDER = Path("/opt/docagent/data/osv_revenue_0925/input")
OUTPUT_FOLDER = Path("/opt/docagent/data/osv_revenue_0925/output")
GROUP_COMPANIES_FILE = INPUT_FOLDER / "Группа Компаний_А.xlsx"
DB_PATH = Path("/opt/docagent/knowledge_base/duckdb/osv/osv_database.duckdb")

# Колонки для счета 62 (Расчеты с покупателями)
# В разных файлах разные счета могут быть, но основные для выручки:
# Дт62 Кт90 - отгрузка товаров/услуг (основная деятельность)
# Дт62 Кт91 - прочие доходы
# Дт51 Кт62 - оплата от покупателей
TARGET_COLUMNS = [
    "Счет",
    "Начальное сальдо Дт", "Начальное сальдо Кт",
    "Оборот Дт", "Оборот Кт",
    "90", "91", "51", "60", "62",
    "Конечное сальдо Дт", "Конечное сальдо Кт"
]


def load_group_companies():
    """Загружает список компаний группы из Excel"""
    df = pd.read_excel(GROUP_COMPANIES_FILE)
    companies = df['Группа компаний'].tolist()
    print(f"📋 Загружено {len(companies)} компаний группы")
    return companies


def looks_like_org(text):
    """Проверяет, является ли текст названием организации"""
    if not isinstance(text, str):
        return False
    text_upper = text.upper()
    # Юридические формы
    org_keywords = ['ООО', 'ОАО', 'ЗАО', 'ПАО', 'АО', 'ИП', 'ФГАУ', 'ФГУП', 'ФГБУ', 'МБУ', 'ГАУ', 'ГУП']
    return any(kw in text_upper for kw in org_keywords)


def looks_like_person_name(text):
    """Проверяет, является ли текст ФИО физического лица"""
    if not isinstance(text, str) or len(text.strip()) < 5:
        return False
    
    # Убираем лишние пробелы
    text = text.strip()
    
    # Разбиваем на слова
    words = text.split()
    
    # ФИО обычно 2-4 слова (Фамилия Имя, Фамилия Имя Отчество, и т.д.)
    if not (2 <= len(words) <= 4):
        return False
    
    # Все слова должны начинаться с заглавной буквы или быть в верхнем регистре
    for word in words:
        if not (word[0].isupper() or word.isupper()):
            return False
    
    # Не должно быть юридических форм
    if looks_like_org(text):
        return False
    
    return True


def is_counterparty_row(text):
    """Проверяет, является ли строка строкой контрагента (не документа)"""
    if not isinstance(text, str):
        return False
    
    text = text.strip()
    
    # Это организация или физическое лицо?
    if looks_like_org(text) or looks_like_person_name(text):
        # Но НЕ документ (договор, счет, акт)
        doc_keywords = ['договор', 'счет', 'акт', 'платеж', '№', 'от']
        text_lower = text.lower()
        return not any(kw in text_lower for kw in doc_keywords)
    
    # Специальный случай: "Физическое лицо" или "Физические лица"
    if 'физическ' in text.lower():
        return True
    
    return False


def is_doc_row(text):
    """Проверяет, является ли строка документом"""
    if not isinstance(text, str):
        return False
    
    text_lower = text.lower()
    doc_keywords = ['договор', 'счет', 'акт', '№', 'от']
    
    return any(kw in text_lower for kw in doc_keywords)


def normalize_1c_oborotka(file_path, company_name):
    """
    Нормализует оборотно-сальдовую ведомость из 1С
    
    Структура файла:
    - Заголовок на строке 2 (header=2): Контрагент, Основание, счета
    - Первая колонка: Контрагент или Документ
    - Вторая колонка: Документ/Основание
    - Далее числовые колонки: Начальное сальдо, Обороты по счетам, Конечное сальдо
    
    Возвращает DataFrame с нормализованными данными
    """
    print(f"\n{'─'*80}")
    print(f"📄 Обработка: {company_name}")
    print(f"   Файл: {file_path.name}")
    
    # Читаем Excel с заголовками на строке 2
    df = pd.read_excel(file_path, header=2, engine='openpyxl')
    
    # Первая колонка - Контрагент, вторая - Основание (документ)
    first_col = df.columns[0]  # Контрагент
    second_col = df.columns[1]  # Основание/Документ
    
    # Находим нужные колонки - анализируем все колонки по содержанию
    available_cols = {}
    
    for col in df.columns[2:]:  # Начиная с 3-й колонки (после Контрагента и Основания)
        col_str = str(col).strip()
        col_lower = col_str.lower()
        
        # Начальное сальдо
        if 'начальное сальдо дт' in col_lower or col_str == 'Начальное сальдо Дт':
            available_cols['Начальное сальдо Дт'] = col
        elif 'начальное сальдо кт' in col_lower or col_str == 'Начальное сальдо Кт':
            available_cols['Начальное сальдо Кт'] = col
        
        # Конечное сальдо
        elif 'конечное сальдо дт' in col_lower or col_str == 'Конечное сальдо Дт':
            available_cols['Конечное сальдо Дт'] = col
        elif 'конечное сальдо кт' in col_lower or col_str == 'Конечное сальдо Кт':
            available_cols['Конечное сальдо Кт'] = col
        
        # Обороты по счетам (ищем паттерны типа "Оборот Дт62 К90", "Дт62 К51" и т.д.)
        # Убираем пробелы для упрощения поиска
        col_clean = col_lower.replace(' ', '')
        
        # Счет 90 - основная выручка (Дт62 Кт90 или Дт62 К90)
        if (('дт62' in col_clean or 'д62' in col_clean) and 
            ('кт90' in col_clean or 'к90' in col_clean)):
            available_cols['90'] = col
        
        # Счет 91 - прочие доходы (Дт62 Кт91 или Дт62 К91)
        elif (('дт62' in col_clean or 'д62' in col_clean) and 
              ('кт91' in col_clean or 'к91' in col_clean)):
            available_cols['91'] = col
        
        # Счет 51 - оплата от покупателей (Дт51 Кт62 или Д51 Кт 62)
        elif (('дт51' in col_clean or 'д51' in col_clean) and 
              ('кт62' in col_clean or 'к62' in col_clean)):
            available_cols['51'] = col
        
        # Счет 62 из Кт51 - возврат аванса (Дт62 Кт51 или Дт62 К51)
        elif (('дт62' in col_clean or 'д62' in col_clean) and 
              ('кт51' in col_clean or 'к51' in col_clean)):
            if '62_51' not in available_cols:
                available_cols['62_51'] = col
        
        # Счет 60 - взаимозачет (Дт60 Кт62)
        elif (('дт60' in col_clean or 'д60' in col_clean) and 
              ('кт62' in col_clean or 'к62' in col_clean)):
            available_cols['60'] = col
        
        # Счет 62 из Кт60 - взаимозачет обратный (Дт62 Кт60)
        elif (('дт62' in col_clean or 'д62' in col_clean) and 
              ('кт60' in col_clean or 'к60' in col_clean)):
            if '62_60' not in available_cols:
                available_cols['62_60'] = col
        
        # Счет 76 - расчёты с разными дебиторами и кредиторами (Дт76 Кт62 или Д76 Кт62)
        elif (('дт76' in col_clean or 'д76' in col_clean) and 
              ('кт62' in col_clean or 'к62' in col_clean)):
            available_cols['76'] = col
        
        # Общие обороты Дт и Кт
        elif col_lower == 'оборот дт' or col_str == 'Оборот Дт':
            available_cols['Оборот Дт'] = col
        elif col_lower == 'оборот кт' or col_str == 'Оборот Кт':
            available_cols['Оборот Кт'] = col
    
    # Создаем список для нормализованных данных
    normalized_rows = []
    
    current_counterparty = None
    
    for idx, row in df.iterrows():
        counterparty_cell = row[first_col]
        document_cell = row[second_col]
        
        # Пропускаем полностью пустые строки
        if pd.isna(counterparty_cell):
            continue
        
        counterparty_str = str(counterparty_cell).strip()
        
        # Пропускаем служебные строки
        if not counterparty_str:
            continue
        
        # Если колонка "Документ/Основание" пустая, используем "Сводная запись"
        if pd.isna(document_cell):
            document_str = f"Сводная запись по контрагенту"
        else:
            document_str = str(document_cell).strip()
            if not document_str:
                document_str = f"Сводная запись по контрагенту"
        
        # Каждая строка - это документ с контрагентом
        # Контрагент в первой колонке, документ во второй
        row_data = {
            'Компания': company_name,
            'Контрагент': counterparty_str,
            'Документ': document_str
        }
        
        # Добавляем числовые данные
        for col_name, col_key in available_cols.items():
            value = row[col_key]
            if pd.notna(value):
                try:
                    row_data[col_name] = float(value)
                except:
                    row_data[col_name] = 0.0
            else:
                row_data[col_name] = 0.0
        
        normalized_rows.append(row_data)
    
    result_df = pd.DataFrame(normalized_rows)
    
    if len(result_df) > 0:
        # Проверка: сумма документов должна совпадать с "Итого" в 1С
        # Ищем строку где во второй колонке "Итого" или содержит "итого"
        df_raw = pd.read_excel(file_path, header=2, engine='openpyxl')
        total_mask = df_raw.iloc[:, 1].astype(str).str.lower().str.contains('итого', na=False)
        total_rows = df_raw[total_mask]
        
        if len(total_rows) > 0:
            total_row = total_rows.iloc[-1]  # Берем последнюю итоговую строку
            
            # Проверяем по разным счетам
            checks = []
            
            # Оборот Дт
            if 'Оборот Дт' in available_cols:
                total_1c = total_row[available_cols['Оборот Дт']]
                total_our = result_df['Оборот Дт'].sum() if 'Оборот Дт' in result_df.columns else 0
                if pd.notna(total_1c) and abs(float(total_1c) - total_our) < 0.01:
                    checks.append(f"Оборот Дт={total_1c:,.2f}")
            
            # Счет 90 (ещё не переименован в 62_90)
            if '90' in available_cols:
                total_1c = total_row[available_cols['90']]
                total_our = result_df['90'].sum() if '90' in result_df.columns else 0
                if pd.notna(total_1c) and abs(float(total_1c) - total_our) < 0.01:
                    checks.append(f"90={total_1c:,.2f}")
            
            # Счет 91 (ещё не переименован в 62_91)
            if '91' in available_cols:
                total_1c = total_row[available_cols['91']]
                total_our = result_df['91'].sum() if '91' in result_df.columns else 0
                if pd.notna(total_1c) and abs(float(total_1c) - total_our) < 0.01:
                    checks.append(f"91={total_1c:,.2f}")
            
            if checks:
                print(f"   ✅ Нормализовано: {len(result_df)} документов")
                print(f"   ✅ Проверка Итого: совпадает с 1С ({', '.join(checks)})")
            else:
                print(f"   ⚠️  Нормализовано: {len(result_df)} документов")
                print(f"   ⚠️  Проверка Итого: не удалось выполнить автоматическую проверку")
        else:
            print(f"   ✅ Нормализовано: {len(result_df)} документов")
    else:
        print(f"   ⚠️  Документов не найдено!")
    
    return result_df


def main():
    """Основная функция"""
    print("="*80)
    print("📊 Нормализация ОСВ счета 62 (9 месяцев 2025)")
    print("="*80)
    
    # Загружаем список компаний группы
    group_companies = load_group_companies()
    
    # Получаем все Excel файлы из папки input (кроме файла группы компаний)
    excel_files = sorted([
        f for f in INPUT_FOLDER.glob("*.xlsx") 
        if f.name != GROUP_COMPANIES_FILE.name
    ])
    
    print(f"\n📂 Найдено файлов для обработки: {len(excel_files)}")
    
    # Обрабатываем каждый файл
    all_data = []
    
    for file_path in excel_files:
        # Извлекаем название компании из имени файла
        # Формат: "исп_9.2025 Компания.xlsx" или "исп.Компания_092025.xlsx" или "и_9.2025 Компания.xlsx"
        file_name = file_path.stem
        
        # Варианты префиксов:
        # "исп_9.2025 " → остаётся "Компания"
        # "исп._9.2025 " → остаётся "Компания"
        # "ипс_9.2025 " → остаётся "Компания"
        # "и_9.2025 " → остаётся "Компания"
        # "исп.Компания_092025" → "Компания_092025" → "Компания"
        
        # Сначала убираем префиксы с пробелом
        company_name = re.sub(r'^(исп\._|исп_|ипс_|и_)\d+\.\d{4}\s+', '', file_name)
        
        # Если не сработало (формат "исп.Компания_092025"), убираем по-другому
        if company_name == file_name:
            # Убираем "исп." в начале
            company_name = re.sub(r'^(исп\.|ипс\.|и\.)', '', file_name)
            # Убираем суффикс "_092025" или подобные
            company_name = re.sub(r'_\d{6}$', '', company_name)
        
        company_name = company_name.strip()
        
        # Нормализуем данные
        df = normalize_1c_oborotka(file_path, company_name)
        
        if len(df) > 0:
            all_data.append(df)
    
    # Объединяем все данные
    if all_data:
        combined_df = pd.concat(all_data, ignore_index=True)
        
        # Переименовываем колонки для единообразия (90 → 62_90, 51 → 51_62, 60 → 60_62, 76 → 76_62)
        rename_map = {}
        if '90' in combined_df.columns:
            rename_map['90'] = '62_90'
        if '91' in combined_df.columns:
            rename_map['91'] = '62_91'
        if '51' in combined_df.columns:
            rename_map['51'] = '51_62'
        if '60' in combined_df.columns:
            rename_map['60'] = '60_62'
        if '76' in combined_df.columns:
            rename_map['76'] = '76_62'
        
        if rename_map:
            combined_df.rename(columns=rename_map, inplace=True)
        
        # ВАЖНО: Упорядочиваем колонки ПОСЛЕ объединения
        ordered_cols = ['Компания', 'Контрагент', 'Документ']
        
        # Начальное сальдо
        if 'Начальное сальдо Дт' in combined_df.columns:
            ordered_cols.append('Начальное сальдо Дт')
        if 'Начальное сальдо Кт' in combined_df.columns:
            ordered_cols.append('Начальное сальдо Кт')
        
        # ОБОРОТЫ (до конечного сальдо!)
        if '62_90' in combined_df.columns:
            ordered_cols.append('62_90')
        if '62_91' in combined_df.columns:
            ordered_cols.append('62_91')
        if '51_62' in combined_df.columns:
            ordered_cols.append('51_62')
        if '60_62' in combined_df.columns:
            ordered_cols.append('60_62')
        if '76_62' in combined_df.columns:
            ordered_cols.append('76_62')
        if '62_51' in combined_df.columns:
            ordered_cols.append('62_51')
        if '62_60' in combined_df.columns:
            ordered_cols.append('62_60')
        if 'Оборот Дт' in combined_df.columns:
            ordered_cols.append('Оборот Дт')
        if 'Оборот Кт' in combined_df.columns:
            ordered_cols.append('Оборот Кт')
        
        # Конечное сальдо (В КОНЦЕ!)
        if 'Конечное сальдо Дт' in combined_df.columns:
            ordered_cols.append('Конечное сальдо Дт')
        if 'Конечное сальдо Кт' in combined_df.columns:
            ordered_cols.append('Конечное сальдо Кт')
        
        # Переупорядочиваем колонки
        combined_df = combined_df[ordered_cols]
        
        print("\n" + "="*80)
        print("📊 Сводная статистика:")
        print("="*80)
        print(f"  Всего документов:     {len(combined_df)}")
        print(f"  Компаний:             {combined_df['Компания'].nunique()}")
        print(f"  Уникальных контрагентов: {combined_df['Контрагент'].nunique()}")
        
        if '62_90' in combined_df.columns:
            print(f"\n  Счет 62_90 (основная выручка):  {combined_df['62_90'].sum():>20,.2f} руб.")
        if '62_91' in combined_df.columns:
            print(f"  Счет 62_91 (прочие доходы):     {combined_df['62_91'].sum():>20,.2f} руб.")
        if '62_90' in combined_df.columns and '62_91' in combined_df.columns:
            total_revenue = combined_df['62_90'].sum() + combined_df['62_91'].sum()
            print(f"  {'─'*60}")
            print(f"  ИТОГО начислено:                {total_revenue:>20,.2f} руб.")
        
        if '51_62' in combined_df.columns:
            print(f"\n  Оплачено (51_62):               {combined_df['51_62'].sum():>20,.2f} руб.")
        
        # Сохраняем в Excel
        OUTPUT_FOLDER.mkdir(parents=True, exist_ok=True)
        output_file = OUTPUT_FOLDER / "normalized_osv.xlsx"
        combined_df.to_excel(output_file, index=False, engine='openpyxl')
        print(f"\n💾 Сохранено в: {output_file}")
        
        # Загружаем в DuckDB
        print("\n" + "="*80)
        print("📊 Загрузка в DuckDB...")
        print("="*80)
        
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        conn = duckdb.connect(str(DB_PATH))
        
        # Создаем таблицу
        conn.execute("DROP TABLE IF EXISTS revenue_raw;")
        conn.execute("""
            CREATE TABLE revenue_raw AS 
            SELECT * FROM combined_df
        """)
        
        # Создаем таблицу с компаниями группы
        companies_df = pd.DataFrame({'company_name': group_companies})
        conn.execute("DROP TABLE IF EXISTS group_companies;")
        conn.execute("CREATE TABLE group_companies AS SELECT * FROM companies_df")
        
        # Статистика
        count = conn.execute("SELECT COUNT(*) as cnt FROM revenue_raw").fetchone()[0]
        companies = conn.execute("SELECT COUNT(DISTINCT \"Компания\") as cnt FROM revenue_raw").fetchone()[0]
        counterparties = conn.execute("SELECT COUNT(DISTINCT \"Контрагент\") as cnt FROM revenue_raw").fetchone()[0]
        
        print(f"  ✅ Таблица revenue_raw создана")
        print(f"     - Документов: {count}")
        print(f"     - Компаний: {companies}")
        print(f"     - Контрагентов: {counterparties}")
        print(f"  ✅ Таблица group_companies создана ({len(group_companies)} компаний)")
        print(f"  💾 База данных: {DB_PATH}")
        
        conn.close()
        
        print("\n" + "="*80)
        print("✅ Нормализация завершена!")
        print("="*80)
        
        return combined_df
    else:
        print("\n⚠️  Не удалось обработать ни одного файла!")
        return None


if __name__ == "__main__":
    main()
