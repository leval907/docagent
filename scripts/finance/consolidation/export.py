"""
Экспорт данных из DuckDB в различные форматы
"""
import duckdb
import yaml
import pandas as pd
from pathlib import Path


def load_config():
    """Загрузка конфигурации"""
    with open('config.yaml', 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def export_to_excel(conn, output_file):
    """Экспорт всех данных в Excel"""
    print(f"\n💾 Экспорт данных в {output_file}...")
    
    with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
        # Все данные
        df_all = conn.execute("SELECT * FROM osv_detailed").df()
        df_all.to_excel(writer, sheet_name='Все данные', index=False)
        
        # По счетам
        df_accounts = conn.execute("SELECT * FROM v_consolidated_by_account").df()
        df_accounts.to_excel(writer, sheet_name='По счетам', index=False)
        
        # По организациям
        df_orgs = conn.execute("SELECT * FROM v_consolidated_by_org").df()
        df_orgs.to_excel(writer, sheet_name='По организациям', index=False)
        
        print(f"✓ Экспортировано листов: 3")


def export_to_csv(conn, output_dir):
    """Экспорт в CSV файлы"""
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)
    
    print(f"\n💾 Экспорт данных в CSV ({output_dir})...")
    
    # Экспорт основных данных
    conn.execute(f"""
        COPY osv_detailed 
        TO '{output_path / "osv_detailed.csv"}' 
        (HEADER, DELIMITER ',')
    """)
    
    # Экспорт консолидаций
    conn.execute(f"""
        COPY v_consolidated_by_account 
        TO '{output_path / "consolidated_by_account.csv"}' 
        (HEADER, DELIMITER ',')
    """)
    
    conn.execute(f"""
        COPY v_consolidated_by_org 
        TO '{output_path / "consolidated_by_org.csv"}' 
        (HEADER, DELIMITER ',')
    """)
    
    print(f"✓ Экспортировано файлов: 3")


def export_to_parquet(conn, output_dir):
    """Экспорт в Parquet формат (для больших данных)"""
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)
    
    print(f"\n💾 Экспорт данных в Parquet ({output_dir})...")
    
    conn.execute(f"""
        COPY osv_detailed 
        TO '{output_path / "osv_detailed.parquet"}' 
        (FORMAT PARQUET)
    """)
    
    print(f"✓ Экспортировано в Parquet")


def main():
    """Основная функция"""
    config = load_config()
    db_path = config['database']['path']
    
    print(f"\n📤 Экспорт данных из {db_path}\n")
    
    conn = duckdb.connect(db_path)
    
    # Экспорт в Excel
    export_to_excel(conn, '../export_results.xlsx')
    
    # Экспорт в CSV
    export_to_csv(conn, '../export_csv')
    
    # Экспорт в Parquet
    export_to_parquet(conn, '../export_parquet')
    
    conn.close()
    
    print("\n✅ Экспорт завершен!")


if __name__ == "__main__":
    main()
