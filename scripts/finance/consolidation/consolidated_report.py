"""
Правильная консолидация группы компаний с исключением внутригрупповых операций
"""
import duckdb
import pandas as pd
import yaml

def load_config():
    """Загрузка конфигурации"""
    with open('config.yaml', 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)

def create_consolidated_report():
    """Создание правильного консолидированного отчета"""
    config = load_config()
    conn = duckdb.connect(config['database']['path'])
    
    print("📊 КОНСОЛИДИРОВАННЫЙ ОТЧЕТ ГРУППЫ КОМПАНИЙ")
    print("="*80)
    print("Период: Первое полугодие 2025 года")
    print("Исключаем внутригрупповые операции для корректной консолидации")
    
    # Определяем компании группы
    group_companies = ['ГРАНДПРОМ', 'ГРОСС ГРУП ДИ', 'ГРОСС ГРУП M', 'СГК-РЕГИОН', 'ЮГ ИСТЕЙТ ИНЖИНИРИНГ']
    
    # 1. Консолидированные обороты по счетам (исключая внутригрупповые)
    print(f"\n💰 1. КОНСОЛИДИРОВАННЫЕ ОБОРОТЫ ПО СЧЕТАМ")
    print("-" * 60)
    
    consolidated_accounts = conn.execute(f"""
        SELECT 
            account,
            -- Количество внешних контрагентов
            COUNT(DISTINCT CASE 
                WHEN subkonto NOT LIKE '%ГРОСС%' 
                 AND subkonto NOT LIKE '%ГРАНДПРОМ%'
                 AND subkonto NOT LIKE '%СГК%'
                 AND subkonto NOT LIKE '%ЮГ%'
                 AND subkonto NOT IN ({','.join([f"'{c}'" for c in group_companies])})
                THEN subkonto END) as external_counterparties,
            
            -- Обороты только с внешними контрагентами
            SUM(CASE 
                WHEN subkonto NOT LIKE '%ГРОСС%' 
                 AND subkonto NOT LIKE '%ГРАНДПРОМ%'
                 AND subkonto NOT LIKE '%СГК%'
                 AND subkonto NOT LIKE '%ЮГ%'
                 AND subkonto NOT IN ({','.join([f"'{c}'" for c in group_companies])})
                THEN turnover_debit ELSE 0 END) as external_debit,
                
            SUM(CASE 
                WHEN subkonto NOT LIKE '%ГРОСС%' 
                 AND subkonto NOT LIKE '%ГРАНДПРОМ%'
                 AND subkonto NOT LIKE '%СГК%'
                 AND subkonto NOT LIKE '%ЮГ%'
                 AND subkonto NOT IN ({','.join([f"'{c}'" for c in group_companies])})
                THEN turnover_credit ELSE 0 END) as external_credit,
                
            -- Остатки с внешними контрагентами
            SUM(CASE 
                WHEN subkonto NOT LIKE '%ГРОСС%' 
                 AND subkonto NOT LIKE '%ГРАНДПРОМ%'
                 AND subkonto NOT LIKE '%СГК%'
                 AND subkonto NOT LIKE '%ЮГ%'
                 AND subkonto NOT IN ({','.join([f"'{c}'" for c in group_companies])})
                THEN closing_debit - closing_credit ELSE 0 END) as external_balance,
                
            -- Внутригрупповые обороты (для справки)
            SUM(CASE 
                WHEN subkonto LIKE '%ГРОСС%' 
                  OR subkonto LIKE '%ГРАНДПРОМ%'
                  OR subkonto LIKE '%СГК%'
                  OR subkonto LIKE '%ЮГ%'
                  OR subkonto IN ({','.join([f"'{c}'" for c in group_companies])})
                THEN turnover_debit + turnover_credit ELSE 0 END) as intercompany_turnover
                
        FROM osv_detailed
        GROUP BY account
        ORDER BY account
    """).df()
    
    account_names = {
        '6001': 'Расчеты с поставщиками (основной долг)',
        '6002': 'Авансы выданные поставщикам',
        '6201': 'Расчеты с покупателями (основной долг)',
        '6202': 'Авансы полученные от покупателей'
    }
    
    for _, row in consolidated_accounts.iterrows():
        account = row['account']
        name = account_names.get(account, 'Неизвестный счет')
        
        print(f"\n🔸 СЧЕТ {account}: {name}")
        print(f"   Внешних контрагентов: {row['external_counterparties']:,}")
        print(f"   Обороты с внешними: Дебет {row['external_debit']:,.0f} ₽, Кредит {row['external_credit']:,.0f} ₽")
        print(f"   Остаток с внешними: {row['external_balance']:,.0f} ₽")
        print(f"   Внутригрупповой оборот: {row['intercompany_turnover']:,.0f} ₽ (исключается)")
    
    # 2. Дебиторская и кредиторская задолженность
    print(f"\n📈 2. ДЕБИТОРСКАЯ И КРЕДИТОРСКАЯ ЗАДОЛЖЕННОСТЬ")
    print("-" * 60)
    
    debt_analysis = conn.execute(f"""
        SELECT 
            CASE 
                WHEN account IN ('6001', '6002') THEN 'Кредиторская задолженность'
                WHEN account IN ('6201', '6202') THEN 'Дебиторская задолженность'
            END as debt_type,
            account,
            
            -- Только внешние остатки
            SUM(CASE 
                WHEN subkonto NOT LIKE '%ГРОСС%' 
                 AND subkonto NOT LIKE '%ГРАНДПРОМ%'
                 AND subkonto NOT LIKE '%СГК%'
                 AND subkonto NOT LIKE '%ЮГ%'
                 AND subkonto NOT IN ({','.join([f"'{c}'" for c in group_companies])})
                THEN closing_debit - closing_credit ELSE 0 END) as net_balance,
                
            COUNT(DISTINCT CASE 
                WHEN subkonto NOT LIKE '%ГРОСС%' 
                 AND subkonto NOT LIKE '%ГРАНДПРОМ%'
                 AND subkonto NOT LIKE '%СГК%'
                 AND subkonto NOT LIKE '%ЮГ%'
                 AND subkonto NOT IN ({','.join([f"'{c}'" for c in group_companies])})
                 AND ABS(closing_debit - closing_credit) > 1000
                THEN subkonto END) as significant_debtors
                
        FROM osv_detailed
        GROUP BY debt_type, account
        ORDER BY debt_type, account
    """).df()
    
    for debt_type in ['Дебиторская задолженность', 'Кредиторская задолженность']:
        type_data = debt_analysis[debt_analysis['debt_type'] == debt_type]
        total_balance = type_data['net_balance'].sum()
        total_debtors = type_data['significant_debtors'].sum()
        
        print(f"\n💳 {debt_type.upper()}: {total_balance:,.0f} ₽")
        print(f"   Значимых контрагентов (>1,000 ₽): {total_debtors}")
        
        for _, row in type_data.iterrows():
            account_name = account_names.get(row['account'], row['account'])
            print(f"   • {row['account']} ({account_name}): {row['net_balance']:,.0f} ₽")
    
    # 3. ТОП-20 внешних контрагентов
    print(f"\n👥 3. ТОП-20 ВНЕШНИХ КОНТРАГЕНТОВ")
    print("-" * 60)
    
    top_external = conn.execute(f"""
        SELECT 
            subkonto,
            SUM(turnover_debit + turnover_credit) as total_turnover,
            SUM(closing_debit - closing_credit) as net_balance,
            COUNT(*) as operations,
            STRING_AGG(DISTINCT account, ', ') as accounts
        FROM osv_detailed
        WHERE subkonto NOT LIKE '%ГРОСС%' 
          AND subkonto NOT LIKE '%ГРАНДПРОМ%'
          AND subkonto NOT LIKE '%СГК%'
          AND subkonto NOT LIKE '%ЮГ%'
          AND subkonto NOT IN ({','.join([f"'{c}'" for c in group_companies])})
          AND subkonto IS NOT NULL
        GROUP BY subkonto
        ORDER BY total_turnover DESC
        LIMIT 20
    """).df()
    
    print("Рейтинг по общему обороту:")
    for i, row in top_external.iterrows():
        debt_type = "Дебитор" if row['net_balance'] > 0 else "Кредитор" if row['net_balance'] < 0 else "Баланс"
        print(f"{i+1:2d}. {row['subkonto'][:45]}")
        print(f"     Оборот: {row['total_turnover']:,.0f} ₽ | Остаток: {row['net_balance']:,.0f} ₽ ({debt_type})")
        print(f"     Операций: {row['operations']} | Счета: {row['accounts']}")
    
    # 4. Сводка по компаниям группы
    print(f"\n🏢 4. ВКЛАД КОМПАНИЙ В ГРУППУ (только внешние операции)")
    print("-" * 60)
    
    company_contribution = conn.execute(f"""
        SELECT 
            company_name,
            SUM(CASE 
                WHEN subkonto NOT LIKE '%ГРОСС%' 
                 AND subkonto NOT LIKE '%ГРАНДПРОМ%'
                 AND subkonto NOT LIKE '%СГК%'
                 AND subkonto NOT LIKE '%ЮГ%'
                 AND subkonto NOT IN ({','.join([f"'{c}'" for c in group_companies])})
                THEN turnover_debit + turnover_credit ELSE 0 END) as external_turnover,
                
            COUNT(DISTINCT CASE 
                WHEN subkonto NOT LIKE '%ГРОСС%' 
                 AND subkonto NOT LIKE '%ГРАНДПРОМ%'
                 AND subkonto NOT LIKE '%СГК%'
                 AND subkonto NOT LIKE '%ЮГ%'
                 AND subkonto NOT IN ({','.join([f"'{c}'" for c in group_companies])})
                THEN subkonto END) as external_counterparties
                
        FROM osv_detailed
        GROUP BY company_name
        ORDER BY external_turnover DESC
    """).df()
    
    total_group_turnover = company_contribution['external_turnover'].sum()
    
    for _, row in company_contribution.iterrows():
        percentage = (row['external_turnover'] / total_group_turnover * 100) if total_group_turnover > 0 else 0
        print(f"• {row['company_name']}")
        print(f"  Внешний оборот: {row['external_turnover']:,.0f} ₽ ({percentage:.1f}% от группы)")
        print(f"  Внешних контрагентов: {row['external_counterparties']:,}")
    
    print(f"\n📊 ИТОГО ПО ГРУППЕ: {total_group_turnover:,.0f} ₽")
    
    # Экспорт в Excel
    print(f"\n💾 Сохранение консолидированного отчета...")
    
    with pd.ExcelWriter('../consolidated_group_report.xlsx', engine='openpyxl') as writer:
        consolidated_accounts.to_excel(writer, sheet_name='Консолидация по счетам', index=False)
        debt_analysis.to_excel(writer, sheet_name='Дебиторка и кредиторка', index=False)
        top_external.to_excel(writer, sheet_name='ТОП внешние контрагенты', index=False)
        company_contribution.to_excel(writer, sheet_name='Вклад компаний', index=False)
    
    print("✅ Отчет сохранен: consolidated_group_report.xlsx")
    
    conn.close()

if __name__ == "__main__":
    create_consolidated_report()