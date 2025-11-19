"""
Импорт OSV Summary файлов в DuckDB
"""
import duckdb
import pandas as pd
import yaml
from pathlib import Path
import glob
import numpy as np


def load_config():
    """Загрузка конфигурации"""
    with open('config.yaml', 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def create_summary_table(conn):
    """Создание таблицы для сводных данных ОСВ"""
    conn.execute("DROP TABLE IF EXISTS osv_summary")
    
    conn.execute("""
        CREATE TABLE osv_summary (
            company_name VARCHAR,
            inn VARCHAR,
            period VARCHAR,
            account VARCHAR,
            account_name VARCHAR,
            opening_debit DECIMAL(18,2),
            opening_credit DECIMAL(18,2),
            turnover_debit DECIMAL(18,2),
            turnover_credit DECIMAL(18,2),
            closing_debit DECIMAL(18,2),
            closing_credit DECIMAL(18,2),
            source_file VARCHAR,
            import_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    conn.execute("CREATE INDEX IF NOT EXISTS idx_summary_company ON osv_summary(company_name)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_summary_account ON osv_summary(account)")


def clean_summary_data(df):
    """Очистка данных OSV Summary"""
    
    # Удаляем unnamed колонки
    df = df.loc[:, ~df.columns.str.contains('^Unnamed')]
    
    # Стандартные колонки для summary
    expected_columns = [
        'company_name', 'inn', 'period', 'account', 'account_name',
        'opening_debit', 'opening_credit', 'turnover_debit', 'turnover_credit',
        'closing_debit', 'closing_credit'
    ]
    
    # Если количество колонок соответствует, переименовываем
    if len(df.columns) == len(expected_columns):
        df.columns = expected_columns
    
    # Удаляем полностью пустые строки
    df = df.dropna(how='all')
    
    # Заполняем NaN в числовых колонках нулями
    numeric_columns = ['opening_debit', 'opening_credit', 'turnover_debit', 
                      'turnover_credit', 'closing_debit', 'closing_credit']
    
    for col in numeric_columns:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
    
    # Очищаем текстовые поля
    text_columns = ['company_name', 'account_name']
    for col in text_columns:
        if col in df.columns:
            df[col] = df[col].astype(str).str.strip()
            df[col] = df[col].replace(['nan', 'None', ''], None)
    
    # Приводим account к строке
    if 'account' in df.columns:
        df['account'] = df['account'].astype(str).str.replace('.0', '', regex=False)
    
    return df


def import_summary_file(file_path, conn):
    """Импорт одного Summary файла"""
    try:
        print(f"📊 Обработка: {file_path.name}")
        
        # Читаем файл
        df = pd.read_excel(file_path)
        
        # Очищаем данные
        df_clean = clean_summary_data(df)
        
        if df_clean.empty:
            print(f"   ⚠️ Файл пустой после очистки")
            return 0
        
        # Добавляем информацию об источнике
        df_clean['source_file'] = file_path.name
        
        # Загружаем в DuckDB
        conn.execute("""
            INSERT INTO osv_summary (
                company_name, inn, period, account, account_name,
                opening_debit, opening_credit, turnover_debit, turnover_credit,
                closing_debit, closing_credit, source_file
            ) SELECT * FROM df_clean
        """)
        
        print(f"   ✅ Загружено записей: {len(df_clean):,}")
        
        # Показываем пример данных
        sample = df_clean.head(2)
        print(f"   📋 Пример данных:")
        print(f"      Компания: {sample['company_name'].iloc[0] if 'company_name' in sample else 'N/A'}")
        print(f"      Счета: {sorted(df_clean['account'].unique())}")
        
        return len(df_clean)
        
    except Exception as e:
        print(f"   ❌ Ошибка: {e}")
        return 0


def main():
    """Основная функция"""
    config = load_config()
    
    # Подключение к существующей базе данных
    db_path = config['database']['path']
    conn = duckdb.connect(db_path)
    
    # Создание таблицы для summary данных
    create_summary_table(conn)
    
    print(f"\n📊 Импорт OSV Summary файлов в {db_path}")
    print("="*80)
    
    total_records = 0
    total_files = 0
    
    # Импорт summary файлов по каждой организации
    for org_config in config['organizations']:
        org_name = org_config['name']
        org_folder = Path(org_config['folder'])
        
        print(f"\n🏢 {org_name}")
        print("-" * 60)
        
        if not org_folder.exists():
            print(f"   ❌ Папка не найдена: {org_folder}")
            continue
        
        # Поиск всех summary файлов
        summary_files = list(org_folder.glob("*osv_summary*.xlsx"))
        
        if not summary_files:
            print(f"   ⚠️ Summary файлы не найдены")
            continue
        
        for file_path in summary_files:
            records = import_summary_file(file_path, conn)
            total_records += records
            total_files += 1
    
    print(f"\n✅ ИМПОРТ SUMMARY ЗАВЕРШЕН!")
    print("="*80)
    print(f"📊 Всего обработано файлов: {total_files}")
    print(f"📈 Всего загружено записей: {total_records:,}")
    
    # Статистика по summary данным
    if total_records > 0:
        print(f"\n📋 СТАТИСТИКА ПО SUMMARY ДАННЫМ:")
        print("-" * 40)
        
        # Общая статистика
        stats = conn.execute("""
            SELECT 
                COUNT(*) as total_records,
                COUNT(DISTINCT company_name) as companies,
                COUNT(DISTINCT account) as accounts
            FROM osv_summary
        """).df()
        
        print(f"Записей: {stats['total_records'].iloc[0]:,}")
        print(f"Компаний: {stats['companies'].iloc[0]}")
        print(f"Счетов: {stats['accounts'].iloc[0]}")
        
        # Статистика по компаниям
        comp_stats = conn.execute("""
            SELECT 
                company_name,
                COUNT(*) as records,
                SUM(turnover_debit) as total_debit,
                SUM(turnover_credit) as total_credit
            FROM osv_summary
            GROUP BY company_name
            ORDER BY total_debit DESC
        """).df()
        
        print(f"\n📊 По компаниям (обороты):")
        for _, row in comp_stats.iterrows():
            print(f"   {row['company_name']}: {row['records']} счетов, "
                  f"Дебет: {row['total_debit']:,.0f}, Кредит: {row['total_credit']:,.0f}")
    
    # Сравнение с детальными данными
    print(f"\n🔍 СРАВНЕНИЕ С ДЕТАЛЬНЫМИ ДАННЫМИ:")
    print("-" * 40)
    
    comparison = conn.execute("""
        SELECT 
            'detailed' as source,
            company_name,
            account,
            SUM(turnover_debit) as debit,
            SUM(turnover_credit) as credit
        FROM osv_detailed
        GROUP BY company_name, account
        
        UNION ALL
        
        SELECT 
            'summary' as source,
            company_name,
            account,
            turnover_debit as debit,
            turnover_credit as credit
        FROM osv_summary
        ORDER BY company_name, account, source
    """).df()
    
    print("Сравнение оборотов (первые 10 записей):")
    print(comparison.head(10).to_string(index=False))
    
    conn.close()


if __name__ == "__main__":
    main()