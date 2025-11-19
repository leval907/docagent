"""
Консолидация данных ОСВ
"""
import duckdb
import yaml
import pandas as pd


def load_config():
    """Загрузка конфигурации"""
    with open('config.yaml', 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def consolidate_by_account(conn):
    """Консолидация по счетам"""
    print("\n📊 Консолидация по счетам...")
    
    result = conn.execute("""
        SELECT 
            account,
            COUNT(*) as total_records,
            SUM(opening_debit - opening_credit) as total_opening_balance,
            SUM(turnover_debit) as total_debit,
            SUM(turnover_credit) as total_credit,
            SUM(closing_debit - closing_credit) as total_closing_balance
        FROM osv_detailed
        GROUP BY account
        ORDER BY account
    """).df()
    
    return result


def consolidate_by_organization(conn):
    """Консолидация по организациям"""
    print("📊 Консолидация по организациям...")
    
    result = conn.execute("""
        SELECT 
            company_name as organization,
            account,
            COUNT(*) as records,
            SUM(opening_debit - opening_credit) as opening_balance,
            SUM(turnover_debit) as debit_turnover,
            SUM(turnover_credit) as credit_turnover,
            SUM(closing_debit - closing_credit) as closing_balance
        FROM osv_detailed
        GROUP BY company_name, account
        ORDER BY company_name, account
    """).df()
    
    return result


def consolidate_by_counterparty(conn):
    """Консолидация по контрагентам (ТОП-50)"""
    print("📊 Консолидация по контрагентам (ТОП-50)...")
    
    result = conn.execute("""
        SELECT 
            subkonto as counterparty,
            SUM(opening_debit - opening_credit) as total_opening_balance,
            SUM(turnover_debit) as total_debit,
            SUM(turnover_credit) as total_credit,
            SUM(closing_debit - closing_credit) as total_closing_balance
        FROM osv_detailed
        WHERE subkonto IS NOT NULL
        GROUP BY subkonto
        ORDER BY ABS(total_closing_balance) DESC
        LIMIT 50
    """).df()
    
    return result


def create_consolidated_views(conn):
    """Создание представлений для консолидации"""
    print("\n🔨 Создание представлений...")
    
    # Представление: Сводка по счетам
    conn.execute("""
        CREATE OR REPLACE VIEW v_consolidated_by_account AS
        SELECT 
            account,
            COUNT(*) as total_records,
            SUM(opening_debit - opening_credit) as total_opening_balance,
            SUM(turnover_debit) as total_debit,
            SUM(turnover_credit) as total_credit,
            SUM(closing_debit - closing_credit) as total_closing_balance
        FROM osv_detailed
        GROUP BY account
    """)
    
    # Представление: Сводка по организациям
    conn.execute("""
        CREATE OR REPLACE VIEW v_consolidated_by_org AS
        SELECT 
            company_name as organization,
            account,
            COUNT(*) as records,
            SUM(opening_debit - opening_credit) as opening_balance,
            SUM(turnover_debit) as debit_turnover,
            SUM(turnover_credit) as credit_turnover,
            SUM(closing_debit - closing_credit) as closing_balance
        FROM osv_detailed
        GROUP BY company_name, account
    """)
    
    print("✓ Представления созданы")


def main():
    """Основная функция"""
    config = load_config()
    db_path = config['database']['path']
    
    print(f"\n🔄 Консолидация данных из {db_path}\n")
    
    conn = duckdb.connect(db_path)
    
    # Создание представлений
    create_consolidated_views(conn)
    
    # Консолидация
    df_accounts = consolidate_by_account(conn)
    df_orgs = consolidate_by_organization(conn)
    df_counterparties = consolidate_by_counterparty(conn)
    
    # Вывод результатов
    print("\n" + "="*80)
    print("КОНСОЛИДАЦИЯ ПО СЧЕТАМ")
    print("="*80)
    print(df_accounts.to_string(index=False))
    
    print("\n" + "="*80)
    print("КОНСОЛИДАЦИЯ ПО ОРГАНИЗАЦИЯМ")
    print("="*80)
    print(df_orgs.to_string(index=False))
    
    print("\n" + "="*80)
    print("ТОП-50 КОНТРАГЕНТОВ")
    print("="*80)
    print(df_counterparties.to_string(index=False))
    
    # Экспорт результатов
    print("\n💾 Экспорт результатов...")
    
    with pd.ExcelWriter('../consolidated_results.xlsx', engine='openpyxl') as writer:
        df_accounts.to_excel(writer, sheet_name='По счетам', index=False)
        df_orgs.to_excel(writer, sheet_name='По организациям', index=False)
        df_counterparties.to_excel(writer, sheet_name='ТОП-50 контрагенты', index=False)
    
    print("✓ Результаты сохранены в: consolidated_results.xlsx")
    
    conn.close()
    print("\n✅ Консолидация завершена!")


if __name__ == "__main__":
    main()
