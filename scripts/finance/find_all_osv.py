"""
Поиск всех файлов ОСВ в папках организаций
"""
import os
from pathlib import Path
import yaml

def load_config():
    """Загрузка конфигурации"""
    with open('config.yaml', 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)

def find_all_osv_files():
    """Поиск всех файлов ОСВ"""
    config = load_config()
    
    print("🔍 ПОИСК ВСЕХ ФАЙЛОВ ОСВ")
    print("="*80)
    
    all_files = []
    
    for org_config in config['organizations']:
        org_name = org_config['name']
        org_folder = Path(org_config['folder'])
        
        print(f"\n🏢 {org_name}")
        print(f"📁 Папка: {org_folder}")
        print("-" * 60)
        
        if not org_folder.exists():
            print(f"❌ Папка не найдена")
            continue
        
        # Все Excel файлы
        excel_files = list(org_folder.glob("*.xlsx")) + list(org_folder.glob("*.xls"))
        
        # Группируем файлы
        osv_detailed = [f for f in excel_files if 'osv_detailed_sql' in f.name.lower()]
        osv_summary = [f for f in excel_files if 'osv_summary' in f.name.lower()]
        osv_regular = [f for f in excel_files if 'осв' in f.name.lower() and 'osv_detailed' not in f.name.lower()]
        other_osv = [f for f in excel_files if any(keyword in f.name.lower() for keyword in ['осв', 'osv']) 
                     and f not in osv_detailed and f not in osv_summary and f not in osv_regular]
        other_files = [f for f in excel_files if f not in osv_detailed + osv_summary + osv_regular + other_osv]
        
        print(f"📊 osv_detailed_sql файлы ({len(osv_detailed)}):")
        for f in osv_detailed:
            print(f"   ✅ {f.name}")
            all_files.append(('osv_detailed', org_name, f))
        
        print(f"\n📋 osv_summary файлы ({len(osv_summary)}):")
        for f in osv_summary:
            print(f"   📈 {f.name}")
            all_files.append(('osv_summary', org_name, f))
        
        print(f"\n🗂️ Обычные ОСВ файлы ({len(osv_regular)}):")
        for f in osv_regular:
            print(f"   📄 {f.name}")
            all_files.append(('osv_regular', org_name, f))
        
        print(f"\n📂 Другие ОСВ файлы ({len(other_osv)}):")
        for f in other_osv:
            print(f"   📎 {f.name}")
            all_files.append(('other_osv', org_name, f))
        
        print(f"\n📁 Прочие Excel файлы ({len(other_files)}):")
        for f in other_files[:5]:  # Показываем только первые 5
            print(f"   📝 {f.name}")
        if len(other_files) > 5:
            print(f"   ... и еще {len(other_files) - 5} файлов")
    
    # Итоговая статистика
    print(f"\n{'='*80}")
    print("📊 ИТОГОВАЯ СТАТИСТИКА")
    print("="*80)
    
    file_types = {}
    for file_type, org, file_path in all_files:
        if file_type not in file_types:
            file_types[file_type] = []
        file_types[file_type].append((org, file_path))
    
    for file_type, files in file_types.items():
        print(f"\n📋 {file_type.upper()}: {len(files)} файлов")
        orgs = {}
        for org, file_path in files:
            if org not in orgs:
                orgs[org] = 0
            orgs[org] += 1
        
        for org, count in orgs.items():
            print(f"   {org}: {count} файлов")
    
    return all_files

if __name__ == "__main__":
    find_all_osv_files()