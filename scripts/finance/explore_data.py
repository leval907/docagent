"""
Исследование структуры данных ОСВ
"""
import os
import pandas as pd
from pathlib import Path
import yaml

def load_config():
    """Загрузка конфигурации"""
    with open('config.yaml', 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)

def explore_excel_file(file_path):
    """Исследование структуры Excel файла"""
    print(f"\n📁 Файл: {file_path.name}")
    print("="*80)
    
    try:
        # Получаем все листы
        excel_file = pd.ExcelFile(file_path)
        sheets = excel_file.sheet_names
        print(f"📋 Листы в файле: {sheets}")
        
        for sheet_name in sheets[:3]:  # Показываем первые 3 листа
            print(f"\n📄 Лист: '{sheet_name}'")
            print("-" * 40)
            
            try:
                # Читаем первые 10 строк
                df = pd.read_excel(file_path, sheet_name=sheet_name, nrows=10)
                print(f"   Размер: {df.shape}")
                print(f"   Колонки: {list(df.columns)}")
                print(f"   Первые строки:")
                print(df.head(3).to_string(index=False))
                
                # Проверяем наличие данных с определенной строки
                if df.shape[0] > 5:
                    df_skip = pd.read_excel(file_path, sheet_name=sheet_name, skiprows=5, nrows=5)
                    if not df_skip.empty:
                        print(f"\n   С 6-й строки:")
                        print(df_skip.head(2).to_string(index=False))
                
            except Exception as e:
                print(f"   ❌ Ошибка чтения листа: {e}")
                
    except Exception as e:
        print(f"❌ Ошибка открытия файла: {e}")

def main():
    """Основная функция"""
    config = load_config()
    
    print("🔍 ИССЛЕДОВАНИЕ СТРУКТУРЫ ДАННЫХ ОСВ")
    print("="*80)
    
    # Исследуем шаблоны
    template_files = [
        "../accounts_template_sorted.xlsx",
        "../osv_detailed_sql_template.xlsx"
    ]
    
    print("\n📋 ШАБЛОНЫ:")
    for template_file in template_files:
        template_path = Path(template_file)
        if template_path.exists():
            explore_excel_file(template_path)
    
    # Исследуем файлы из каждой организации
    print("\n🏢 ФАЙЛЫ ОРГАНИЗАЦИЙ:")
    
    for org_config in config['organizations'][:2]:  # Первые 2 организации
        org_name = org_config['name']
        org_folder = Path(org_config['folder'])
        
        print(f"\n{'='*80}")
        print(f"🏢 ОРГАНИЗАЦИЯ: {org_name}")
        print(f"📁 Папка: {org_folder}")
        print("="*80)
        
        if not org_folder.exists():
            print(f"❌ Папка не существует: {org_folder}")
            continue
            
        # Ищем файлы osv_detailed_sql_*.xlsx
        osv_files = list(org_folder.glob("osv_detailed_sql_*.xlsx"))
        
        if osv_files:
            print(f"📊 Найдено {len(osv_files)} файлов ОСВ:")
            for file_path in osv_files[:2]:  # Первые 2 файла
                explore_excel_file(file_path)
        else:
            print("❌ Файлы osv_detailed_sql_*.xlsx не найдены")
            
            # Показываем все Excel файлы в папке
            all_excel = list(org_folder.glob("*.xlsx")) + list(org_folder.glob("*.xls"))
            if all_excel:
                print(f"\n📄 Все Excel файлы в папке ({len(all_excel)}):")
                for file_path in all_excel[:5]:  # Первые 5
                    print(f"   - {file_path.name}")
                    
                # Исследуем первый файл
                if all_excel:
                    explore_excel_file(all_excel[0])

if __name__ == "__main__":
    main()