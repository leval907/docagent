"""
Импорт данных ОСВ в DuckDB
"""
import duckdb
import pandas as pd
import yaml
from pathlib import Path
import glob


def load_config():
    """Загрузка конфигурации"""
    with open('config.yaml', 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def create_database(db_path):
    """Создание базы данных и схемы"""
    conn = duckdb.connect(db_path)
    
    # Создание таблицы для детальных данных ОСВ
    conn.execute("""
        CREATE TABLE IF NOT EXISTS osv_detailed (
            organization VARCHAR,
            account VARCHAR,
            counterparty VARCHAR,
            contract VARCHAR,
            opening_balance DECIMAL(18,2),
            debit_turnover DECIMAL(18,2),
            credit_turnover DECIMAL(18,2),
            closing_balance DECIMAL(18,2),
            import_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Создание индексов
    conn.execute("CREATE INDEX IF NOT EXISTS idx_org ON osv_detailed(organization)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_account ON osv_detailed(account)")
    
    return conn


def import_excel_file(file_path, organization, account):
    """Импорт одного Excel файла"""
    try:
        df = pd.read_excel(file_path)
        
        # Добавляем метаданные
        df['organization'] = organization
        df['account'] = account
        
        print(f"✓ Импортирован: {file_path.name} ({len(df)} записей)")
        return df
    except Exception as e:
        print(f"✗ Ошибка при импорте {file_path}: {e}")
        return None


def main():
    """Основная функция"""
    config = load_config()
    
    # Создание базы данных
    db_path = config['database']['path']
    conn = create_database(db_path)
    
    print(f"\n📊 Начало импорта данных в {db_path}\n")
    
    total_records = 0
    
    # Импорт данных по каждой организации
    for org_config in config['organizations']:
        org_name = org_config['name']
        org_folder = Path(org_config['folder'])
        
        print(f"\n🏢 Организация: {org_name}")
        print(f"   Папка: {org_folder}")
        
        # Поиск всех файлов osv_detailed_sql_*.xlsx
        pattern = str(org_folder / "osv_detailed_sql_*.xlsx")
        files = glob.glob(pattern)
        
        for file_path in files:
            file_path = Path(file_path)
            
            # Извлечение номера счета из имени файла
            # Формат: osv_detailed_sql_ОСВ_60.01_DI.xlsx
            parts = file_path.stem.split('_')
            if len(parts) >= 4:
                account = parts[3]  # 60.01
            else:
                account = 'unknown'
            
            df = import_excel_file(file_path, org_name, account)
            
            if df is not None:
                # Загрузка в DuckDB
                conn.execute("INSERT INTO osv_detailed SELECT * FROM df")
                total_records += len(df)
    
    print(f"\n✅ Импорт завершен!")
    print(f"   Всего загружено записей: {total_records:,}")
    
    # Статистика
    stats = conn.execute("""
        SELECT 
            organization,
            account,
            COUNT(*) as records
        FROM osv_detailed
        GROUP BY organization, account
        ORDER BY organization, account
    """).df()
    
    print("\n📈 Статистика по организациям и счетам:")
    print(stats.to_string(index=False))
    
    conn.close()


if __name__ == "__main__":
    main()
