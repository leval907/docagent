#!/usr/bin/env python3
"""
Импорт общих оборотно-сальдовых ведомостей (ОСВ) в DuckDB.
Файлы содержат сводные данные по всем счетам (01, 02, ..., 99).
"""

import pandas as pd
import duckdb
from pathlib import Path
import re
import os

# === Настройки ===
INPUT_FOLDER = Path("/opt/docagent/data/osv_revenue_0925/input/osv_9_month/ОСВ 9 мес")
DB_PATH = Path("/opt/docagent/knowledge_base/duckdb/osv/osv_database.duckdb")

def normalize_company_name(filename):
    """Извлекает название компании из имени файла"""
    # Пример: "ОСВ 9 А.xlsx" -> "А" -> "Альянс" (нужен маппинг или эвристика)
    name = filename.replace("ОСВ 9 ", "").replace(".xlsx", "").strip()
    return name

def parse_general_osv(file_path):
    print(f"📄 Обработка: {file_path.name}")
    
    # Читаем файл
    try:
        # Сначала читаем первые строки, чтобы найти заголовок и название компании
        header_df = pd.read_excel(file_path, header=None, nrows=10)
        
        company_name_in_file = header_df.iloc[0, 0] if not pd.isna(header_df.iloc[0, 0]) else ""
        print(f"   Название в файле: {company_name_in_file}")
        
        # Ищем строку с заголовком "Счет"
        header_row_idx = -1
        for idx, row in header_df.iterrows():
            row_str = row.astype(str).str.lower().tolist()
            if any("счет" in s for s in row_str):
                header_row_idx = idx
                break
        
        if header_row_idx == -1:
            print("   ❌ Не найден заголовок таблицы")
            return None

        # Читаем данные, пропуская строки до заголовка + 1 (строка с Дебет/Кредит)
        # Фактически данные начинаются через 2 строки после "Счет"
        # Row 5: Счет ...
        # Row 6: ... Дебет Кредит ...
        # Row 7: Данные
        
        df = pd.read_excel(file_path, header=None, skiprows=header_row_idx + 2)
        
        # Ожидаем 7 колонок: Счет, Нач.Дт, Нач.Кт, Об.Дт, Об.Кт, Кон.Дт, Кон.Кт
        # Но в Excel может быть больше колонок (пустые и т.д.)
        # Обычно структура: A=Счет, B=НачДт, C=НачКт, D=ОбДт, E=ОбКт, F=КонДт, G=КонКт
        
        # Берем первые 7 колонок
        df = df.iloc[:, :7]
        df.columns = ['account', 'start_dt', 'start_kt', 'turn_dt', 'turn_kt', 'end_dt', 'end_kt']
        
        # Фильтруем строки
        data_rows = []
        for _, row in df.iterrows():
            account = str(row['account']).strip()
            
            # Пропускаем пустые или "Итого"
            if pd.isna(row['account']) or account.lower() == 'nan':
                continue
            if 'итого' in account.lower():
                continue
                
            # Очистка числовых данных
            def clean_num(val):
                if pd.isna(val): return 0.0
                if isinstance(val, (int, float)): return float(val)
                try:
                    return float(str(val).replace('\xa0', '').replace(' ', '').replace(',', '.'))
                except:
                    return 0.0

            row_data = {
                'filename': file_path.name,
                'company_raw': company_name_in_file,
                'period': '9_months_2025',  # Добавлено поле периода
                'account': account,
                'start_dt': clean_num(row['start_dt']),
                'start_kt': clean_num(row['start_kt']),
                'turn_dt': clean_num(row['turn_dt']),
                'turn_kt': clean_num(row['turn_kt']),
                'end_dt': clean_num(row['end_dt']),
                'end_kt': clean_num(row['end_kt'])
            }
            data_rows.append(row_data)
            
        return pd.DataFrame(data_rows)
        
    except Exception as e:
        print(f"   ❌ Ошибка обработки: {e}")
        return None

def main():
    print("="*80)
    print("📊 Импорт общих ОСВ (9 месяцев)")
    print("="*80)
    
    if not INPUT_FOLDER.exists():
        print(f"❌ Папка не найдена: {INPUT_FOLDER}")
        return

    files = sorted([f for f in INPUT_FOLDER.glob("*.xlsx") if not f.name.startswith("~$")])
    print(f"📂 Найдено файлов: {len(files)}")
    
    all_data = []
    for f in files:
        df = parse_general_osv(f)
        if df is not None and not df.empty:
            all_data.append(df)
            print(f"   ✅ Загружено строк: {len(df)}")
    
    if all_data:
        full_df = pd.concat(all_data, ignore_index=True)
        
        # Сохраняем в DuckDB
        print("\n🦆 Сохранение в DuckDB...")
        conn = duckdb.connect(str(DB_PATH))
        conn.execute("CREATE TABLE IF NOT EXISTS osv_general AS SELECT * FROM full_df WHERE 1=0")
        # Очищаем старые данные из этой загрузки (если нужно) или просто добавляем
        # Для простоты пересоздадим таблицу или добавим
        conn.execute("DROP TABLE IF EXISTS osv_general")
        conn.execute("CREATE TABLE osv_general AS SELECT * FROM full_df")
        
        count = conn.execute("SELECT COUNT(*) FROM osv_general").fetchone()[0]
        print(f"✅ Всего записей в таблице osv_general: {count}")
        
        # Пример анализа: Выручка (счет 90.01)
        print("\n📊 Пример: Выручка (Кредитовый оборот 90.01)")
        res = conn.execute("""
            SELECT company_raw, SUM(turn_kt) as revenue 
            FROM osv_general 
            WHERE account LIKE '90.01%' 
            GROUP BY company_raw 
            ORDER BY revenue DESC
        """).fetchdf()
        print(res)
        
        conn.close()
    else:
        print("⚠️  Нет данных для сохранения")

if __name__ == "__main__":
    main()
