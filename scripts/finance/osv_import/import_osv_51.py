#!/usr/bin/env python3
"""
Импорт ОСВ по счету 51 (Денежные средства) в DuckDB.
Файлы содержат обороты по статьям движения денежных средств (ДДС).
"""

import pandas as pd
import duckdb
from pathlib import Path
import os

# === Настройки ===
INPUT_FOLDER = Path("/opt/docagent/data/osv_revenue_0925/input/osv_51_9m/51")
DB_PATH = Path("/opt/docagent/knowledge_base/duckdb/osv/osv_database.duckdb")

def parse_osv_51(file_path):
    print(f"📄 Обработка: {file_path.name}")
    
    try:
        # 1. Читаем заголовок для названия компании (первые 10 строк)
        header_raw = pd.read_excel(file_path, header=None, nrows=10)
        company_name = header_raw.iloc[0, 0] if not pd.isna(header_raw.iloc[0, 0]) else ""
        print(f"   Компания: {company_name}")
        
        # 2. Ищем строку с заголовками колонок
        header_row_idx = -1
        for idx, row in header_raw.iterrows():
            row_str = row.astype(str).str.lower().tolist()
            # Ищем ключевые слова заголовка
            if any("счет" in s for s in row_str) and any("оборот дт" in s for s in row_str):
                header_row_idx = idx
                break
        
        if header_row_idx == -1:
            print("   ❌ Не найден заголовок таблицы (строка с 'Счет' и 'Оборот Дт')")
            return None
            
        # 3. Читаем данные с правильным заголовком
        df = pd.read_excel(file_path, header=header_row_idx)
        
        # Очищаем имена колонок
        df.columns = [str(c).strip().replace('\n', ' ') for c in df.columns]
        
        # 4. Определяем индексы ключевых колонок
        try:
            # Ищем колонку со статьями (обычно первая или называется "Счет" или "Статьи...")
            # В файле 01-51 А.xlsx колонка называется "Счет", но под ней идут статьи
            col_dds_idx = 0 
            
            # Ищем Оборот Дт и Оборот Кт
            col_turn_dt_idx = -1
            col_turn_kt_idx = -1
            
            for i, col in enumerate(df.columns):
                c_lower = col.lower()
                if "оборот дт" in c_lower and "сальдо" not in c_lower:
                    col_turn_dt_idx = i
                elif "оборот кт" in c_lower and "сальдо" not in c_lower:
                    col_turn_kt_idx = i
            
            if col_turn_dt_idx == -1 or col_turn_kt_idx == -1:
                print(f"   ❌ Не найдены колонки оборотов. Дт: {col_turn_dt_idx}, Кт: {col_turn_kt_idx}")
                return None
                
            # 5. Определяем колонки для исключения (счет 51)
            exclude_dt_indices = []
            exclude_kt_indices = []
            
            for i, col in enumerate(df.columns):
                col_clean = col.replace('.0', '').replace('.00', '').strip()
                if col_clean == '51':
                    if col_turn_dt_idx < i < col_turn_kt_idx:
                        exclude_dt_indices.append(i)
                    elif i > col_turn_kt_idx:
                        exclude_kt_indices.append(i)
            
            # print(f"   Индексы: Дт={col_turn_dt_idx}, Кт={col_turn_kt_idx}")
            # print(f"   Исключить Дт (51): {exclude_dt_indices}")
            # print(f"   Исключить Кт (51): {exclude_kt_indices}")

        except Exception as e:
            print(f"   ❌ Ошибка анализа колонок: {e}")
            return None

        # 6. Извлекаем данные
        data_rows = []
        
        # Функция очистки чисел
        def clean_num(val):
            if pd.isna(val): return 0.0
            if isinstance(val, (int, float)): return float(val)
            try:
                return float(str(val).replace('\xa0', '').replace(' ', '').replace(',', '.'))
            except:
                return 0.0

        for _, row in df.iterrows():
            # Статья ДДС
            dds_val = row.iloc[col_dds_idx]
            if pd.isna(dds_val):
                continue
            
            dds_str = str(dds_val).strip()
            if dds_str.lower() in ['nan', 'итого', 'счет']: # 'счет' может попасться если заголовок размазан
                continue
            
            # Пропускаем строки с номерами счетов (например "51") если они вдруг попали как данные
            if dds_str == '51':
                continue

            # Основные суммы
            turn_dt = clean_num(row.iloc[col_turn_dt_idx])
            turn_kt = clean_num(row.iloc[col_turn_kt_idx])
            
            if turn_dt == 0 and turn_kt == 0:
                continue
                
            # Суммы для исключения
            internal_dt = sum(clean_num(row.iloc[i]) for i in exclude_dt_indices)
            internal_kt = sum(clean_num(row.iloc[i]) for i in exclude_kt_indices)
            
            final_inflow = turn_dt - internal_dt
            final_outflow = turn_kt - internal_kt
            
            # Округляем
            final_inflow = round(final_inflow, 2)
            final_outflow = round(final_outflow, 2)
            
            row_data = {
                'filename': file_path.name,
                'company_raw': company_name,
                'period': '9_months_2025',
                'dds_item': dds_str,
                'inflow': final_inflow,
                'outflow': final_outflow,
                'internal_move_dt': internal_dt,
                'internal_move_kt': internal_kt
            }
            data_rows.append(row_data)
            
        return pd.DataFrame(data_rows)

    except Exception as e:
        print(f"   ❌ Ошибка: {e}")
        return None

def main():
    print("="*80)
    print("💰 Импорт ОСВ по счету 51 (ДДС)")
    print("="*80)
    
    if not INPUT_FOLDER.exists():
        print(f"❌ Папка не найдена: {INPUT_FOLDER}")
        return
        
    files = sorted([f for f in INPUT_FOLDER.glob("*.xlsx") if not f.name.startswith("~$")])
    print(f"📂 Найдено файлов: {len(files)}")
    
    all_data = []
    for f in files:
        df = parse_osv_51(f)
        if df is not None and not df.empty:
            all_data.append(df)
            print(f"   ✅ Загружено строк: {len(df)}")
            
    if all_data:
        full_df = pd.concat(all_data, ignore_index=True)
        
        print("\n🦆 Сохранение в DuckDB...")
        conn = duckdb.connect(str(DB_PATH))
        conn.execute("DROP TABLE IF EXISTS osv_51")
        conn.execute("CREATE TABLE osv_51 AS SELECT * FROM full_df")
        
        count = conn.execute("SELECT COUNT(*) FROM osv_51").fetchone()[0]
        print(f"✅ Всего записей в таблице osv_51: {count}")
        
        # Пример: Топ статей расхода
        print("\n📊 Топ-5 статей расхода (Outflow):")
        res = conn.execute("""
            SELECT dds_item, SUM(outflow) as total_out 
            FROM osv_51 
            GROUP BY dds_item 
            ORDER BY total_out DESC 
            LIMIT 5
        """).fetchdf()
        print(res)
        
        conn.close()
    else:
        print("⚠️  Нет данных для сохранения")

if __name__ == "__main__":
    main()
