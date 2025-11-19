"""
Исследование структуры всех типов файлов ОСВ
"""
import pandas as pd
from pathlib import Path
import yaml

def load_config():
    """Загрузка конфигурации"""
    with open('config.yaml', 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)

def explore_file_structure(file_path, file_type):
    """Исследование структуры файла"""
    print(f"\n📁 {file_type}: {file_path.name}")
    print("="*80)
    
    try:
        # Получаем все листы
        excel_file = pd.ExcelFile(file_path)
        sheets = excel_file.sheet_names
        print(f"📋 Листы: {sheets}")
        
        for sheet_name in sheets[:2]:  # Первые 2 листа
            print(f"\n📄 Лист: '{sheet_name}'")
            print("-" * 40)
            
            try:
                # Читаем первые 15 строк
                df = pd.read_excel(file_path, sheet_name=sheet_name, nrows=15)
                print(f"   Размер: {df.shape}")
                print(f"   Колонки: {list(df.columns)}")
                
                # Показываем данные
                if not df.empty:
                    print(f"   Первые строки:")
                    print(df.head(5).to_string(index=False, max_colwidth=20))
                
                    # Проверяем с разными skiprows
                    for skip in [1, 2, 3, 5]:
                        try:
                            df_skip = pd.read_excel(file_path, sheet_name=sheet_name, skiprows=skip, nrows=5)
                            if not df_skip.empty and df_skip.shape[1] > 5:
                                print(f"\n   Со строки {skip+1}:")
                                print(df_skip.head(2).to_string(index=False, max_colwidth=20))
                                break
                        except:
                            continue
                
            except Exception as e:
                print(f"   ❌ Ошибка чтения листа: {e}")
                
    except Exception as e:
        print(f"❌ Ошибка открытия файла: {e}")

def main():
    """Основная функция"""
    config = load_config()
    
    print("🔍 ИССЛЕДОВАНИЕ ВСЕХ ТИПОВ ФАЙЛОВ ОСВ")
    print("="*80)
    
    # Исследуем файлы разных типов
    for org_config in config['organizations'][:2]:  # Первые 2 организации
        org_name = org_config['name']
        org_folder = Path(org_config['folder'])
        
        print(f"\n{'='*80}")
        print(f"🏢 ОРГАНИЗАЦИЯ: {org_name}")
        print("="*80)
        
        if not org_folder.exists():
            continue
        
        # OSV Summary файлы
        summary_files = list(org_folder.glob("*osv_summary*.xlsx"))
        if summary_files:
            explore_file_structure(summary_files[0], "OSV SUMMARY")
        
        # Обычные ОСВ файлы
        osv_files = [f for f in org_folder.glob("*.xlsx") if 'осв' in f.name.lower() and 'osv_detailed' not in f.name.lower()]
        if not osv_files:
            osv_files = [f for f in org_folder.glob("*.xls") if 'осв' in f.name.lower()]
        
        if osv_files:
            explore_file_structure(osv_files[0], "OSV REGULAR")
        
        # Файлы отдельных счетов
        account_files = []
        for pattern in ["*60.01*", "*60.02*", "*62.01*", "*62.02*"]:
            account_files.extend(org_folder.glob(pattern))
        
        if account_files:
            # Берем файл 60.01
            file_6001 = [f for f in account_files if '60.01' in f.name]
            if file_6001:
                explore_file_structure(file_6001[0], "ACCOUNT FILE (60.01)")

if __name__ == "__main__":
    main()