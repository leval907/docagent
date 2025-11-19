#!/usr/bin/env python3
"""
Детальная проверка нормализации для компании Владение-В
"""

import pandas as pd
from pathlib import Path

# Настройки
INPUT_FILE = Path("/opt/docagent/data/osv_revenue_0925/input/9.2025 Владение-В.xlsx")
NORMALIZED_FILE = Path("/opt/docagent/data/osv_revenue_0925/output/normalized_osv.xlsx")


def check_vladenie_v():
    print("="*100)
    print("🔍 ПРОВЕРКА КОМПАНИИ: ВЛАДЕНИЕ-В")
    print("="*100)
    
    # 1. Читаем исходный Excel файл
    print("\n📂 Читаем исходный файл Excel...")
    df_excel = pd.read_excel(INPUT_FILE, engine='openpyxl', header=None)
    
    # Находим строку "Итого"
    mask_itogo = df_excel[0].astype(str).str.lower().str.contains("итого", na=False)
    itogo_rows = df_excel[mask_itogo]
    
    if len(itogo_rows) > 0:
        itogo_row = itogo_rows.iloc[-1]  # Берем последнюю строку "Итого"
        print("\n📊 Итоговая строка из 1С (строка 'Итого'):")
        print(f"   Оборот Дт: {itogo_row[5]:>15,.2f}" if pd.notna(itogo_row[5]) else "")
        print(f"   Оборот Кт: {itogo_row[6]:>15,.2f}" if pd.notna(itogo_row[6]) else "")
        print(f"   Счет 90:   {itogo_row[10]:>15,.2f}" if pd.notna(itogo_row[10]) else "")
        print(f"   Счет 91:   {itogo_row[11]:>15,.2f}" if pd.notna(itogo_row[11]) else "")
    
    # 2. Читаем нормализованные данные
    print("\n📂 Читаем нормализованный файл...")
    df_norm = pd.read_excel(NORMALIZED_FILE, engine='openpyxl')
    vladenie = df_norm[df_norm['Компания'] == 'Владение-В'].copy()
    
    print(f"\n📊 Нормализованные данные:")
    print(f"   Всего документов: {len(vladenie)}")
    print(f"   Уникальных контрагентов: {vladenie['Контрагент'].nunique()}")
    
    # Суммы
    sum_oborot_dt = vladenie['Оборот Дт'].sum()
    sum_oborot_kt = vladenie['Оборот Кт'].sum()
    sum_90 = vladenie['90'].sum()
    sum_91 = vladenie['91'].sum()
    
    print(f"\n💰 Суммы по нормализованным данным:")
    print(f"   Оборот Дт: {sum_oborot_dt:>15,.2f}")
    print(f"   Оборот Кт: {sum_oborot_kt:>15,.2f}")
    print(f"   Счет 90:   {sum_90:>15,.2f}")
    print(f"   Счет 91:   {sum_91:>15,.2f}")
    
    # 3. Показываем все контрагенты
    print("\n" + "="*100)
    print("📋 СПИСОК ВСЕХ КОНТРАГЕНТОВ:")
    print("="*100)
    
    vladenie_sorted = vladenie.sort_values(['Контрагент', 'Документ'])
    
    for idx, row in vladenie_sorted.iterrows():
        print(f"\n{'='*100}")
        print(f"Контрагент: {row['Контрагент']}")
        print(f"Документ:   {row['Документ']}")
        print(f"   Оборот Дт: {row['Оборот Дт']:>12,.2f}  |  Оборот Кт: {row['Оборот Кт']:>12,.2f}")
        print(f"   Счет 90:   {row['90']:>12,.2f}  |  Счет 91:   {row['91']:>12,.2f}")
    
    # 4. Показываем исходный Excel для сравнения
    print("\n\n" + "="*100)
    print("📄 ИСХОДНЫЙ EXCEL (все строки кроме 'Итого'):")
    print("="*100)
    
    df_excel_clean = df_excel[~mask_itogo].copy()
    
    for idx, row in df_excel_clean.iterrows():
        if pd.notna(row[0]):
            text = str(row[0])[:80]
            oborot_dt = f"{row[5]:>12,.2f}" if pd.notna(row[5]) and row[5] != 0 else ''
            oborot_kt = f"{row[6]:>12,.2f}" if pd.notna(row[6]) and row[6] != 0 else ''
            col90 = f"{row[10]:>12,.2f}" if pd.notna(row[10]) and row[10] != 0 else ''
            col91 = f"{row[11]:>12,.2f}" if pd.notna(row[11]) and row[11] != 0 else ''
            
            if oborot_dt or oborot_kt or col90 or col91:
                print(f"\n{text}")
                if oborot_dt:
                    print(f"   Оборот Дт: {oborot_dt}")
                if oborot_kt:
                    print(f"   Оборот Кт: {oborot_kt}")
                if col90:
                    print(f"   Счет 90:   {col90}")
                if col91:
                    print(f"   Счет 91:   {col91}")
    
    # Сохраняем в Excel для удобства
    output_file = Path("/opt/docagent/data/osv_revenue_0925/output/check_vladenie_v.xlsx")
    
    export_df = vladenie_sorted[[
        'Контрагент', 'Документ', 
        'Начальное сальдо Дт', 'Начальное сальдо Кт',
        'Оборот Дт', 'Оборот Кт', 
        '90', '91', '51', '62',
        'Конечное сальдо Дт', 'Конечное сальдо Кт'
    ]].copy()
    
    export_df.to_excel(output_file, index=False, engine='openpyxl')
    
    print("\n" + "="*100)
    print(f"💾 Детальный отчет сохранен: {output_file}")
    print("="*100)


if __name__ == "__main__":
    check_vladenie_v()
