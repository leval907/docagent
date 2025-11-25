{{
    config(
        materialized='table',
        schema='analytics'
    )
}}

WITH company_activity AS (
    SELECT 
        c.company_code,
        c.company_name,
        c.inn,
        c.primary_okved as okved_code,
        CASE 
            WHEN c.primary_okved LIKE '68%' THEN 'Операции с недвижимостью'
            WHEN c.primary_okved LIKE '71%' THEN 'Архитектура и инженерные изыскания'
            WHEN c.primary_okved LIKE '43%' THEN 'Строительство специализированное'
            WHEN c.primary_okved LIKE '41%' THEN 'Строительство зданий'
            WHEN c.primary_okved LIKE '42%' THEN 'Строительство инженерных сооружений'
            WHEN c.primary_okved LIKE '62%' THEN 'IT-разработка и услуги'
            WHEN c.primary_okved LIKE '73%' THEN 'Реклама и маркетинговые исследования'
            WHEN c.primary_okved LIKE '81%' THEN 'Обслуживание зданий и территорий'
            WHEN c.primary_okved LIKE '86%' THEN 'Здравоохранение'
            ELSE 'Прочие виды деятельности'
        END as activity_type,
        CASE 
            WHEN c.primary_okved LIKE '68%' THEN 1
            WHEN c.primary_okved LIKE '71%' THEN 2
            WHEN c.primary_okved LIKE '81%' THEN 3
            WHEN c.primary_okved LIKE '43%' OR c.primary_okved LIKE '41%' OR c.primary_okved LIKE '42%' THEN 4
            WHEN c.primary_okved LIKE '62%' THEN 5
            ELSE 9
        END as activity_sort_order,
        c.is_active
    FROM {{ source('master', 'companies') }} c
),

financial_summary AS (
    SELECT 
        company_id,
        -- Выручка (90.01)
        SUM(CASE WHEN account_code = '90.01' THEN credit_turnover ELSE 0 END) as revenue,
        -- Себестоимость продаж (90.02)
        SUM(CASE WHEN account_code = '90.02' THEN debit_turnover ELSE 0 END) as cost_of_sales,
        -- Коммерческие расходы (90.07)
        SUM(CASE WHEN account_code = '90.07' THEN debit_turnover ELSE 0 END) as selling_expenses,
        -- Управленческие расходы (90.08)
        SUM(CASE WHEN account_code = '90.08' THEN debit_turnover ELSE 0 END) as admin_expenses,
        -- Прочие доходы (91.01)
        SUM(CASE WHEN account_code LIKE '91.01%' THEN credit_turnover ELSE 0 END) as other_income,
        -- Прочие расходы (91.02)
        SUM(CASE WHEN account_code LIKE '91.02%' THEN debit_turnover ELSE 0 END) as other_expenses,
        -- Финансовый результат (99)
        SUM(CASE WHEN account_code LIKE '99%' THEN credit_turnover - debit_turnover ELSE 0 END) as net_profit
    FROM {{ source('history', 'osv_9m_summary') }}
    GROUP BY company_id
),

companies_enriched AS (
    SELECT 
        c.id,
        c.company_code,
        c.company_name
    FROM {{ source('master', 'companies') }} c
)

SELECT 
    ca.company_code,
    ca.company_name,
    ca.inn,
    ca.activity_type,
    ca.okved_code,
    ca.activity_sort_order,
    ca.is_active,
    
    -- Финансовые показатели
    ROUND(COALESCE(fs.revenue, 0)::numeric, 2) as revenue,
    ROUND(COALESCE(fs.cost_of_sales, 0)::numeric, 2) as cost_of_sales,
    ROUND(COALESCE(fs.selling_expenses, 0)::numeric, 2) as selling_expenses,
    ROUND(COALESCE(fs.admin_expenses, 0)::numeric, 2) as admin_expenses,
    ROUND(COALESCE(fs.other_income, 0)::numeric, 2) as other_income,
    ROUND(COALESCE(fs.other_expenses, 0)::numeric, 2) as other_expenses,
    ROUND(COALESCE(fs.net_profit, 0)::numeric, 2) as net_profit,
    
    -- Рассчитываемые метрики
    ROUND((COALESCE(fs.cost_of_sales, 0) + COALESCE(fs.selling_expenses, 0) + COALESCE(fs.admin_expenses, 0))::numeric, 2) as total_expenses,
    
    ROUND(
        CASE 
            WHEN COALESCE(fs.revenue, 0) > 0 
            THEN (COALESCE(fs.cost_of_sales, 0) / fs.revenue * 100)::numeric
            ELSE 0 
        END, 
        2
    ) as cost_to_revenue_pct,
    
    ROUND(
        CASE 
            WHEN COALESCE(fs.revenue, 0) > 0 
            THEN (COALESCE(fs.net_profit, 0) / fs.revenue * 100)::numeric
            ELSE 0 
        END, 
        2
    ) as profit_margin_pct,
    
    -- Классификация компании
    CASE 
        WHEN COALESCE(fs.revenue, 0) < 100000 THEN 'Неактивная'
        WHEN COALESCE(fs.net_profit, 0) > 0 THEN 'Прибыльная'
        ELSE 'Убыточная'
    END as profitability_status,
    
    CASE 
        WHEN COALESCE(fs.revenue, 0) >= 500000000 THEN 'Крупная'
        WHEN COALESCE(fs.revenue, 0) >= 100000000 THEN 'Средняя'
        WHEN COALESCE(fs.revenue, 0) >= 10000000 THEN 'Малая'
        WHEN COALESCE(fs.revenue, 0) > 0 THEN 'Микро'
        ELSE 'Нулевая'
    END as company_size

FROM company_activity ca
LEFT JOIN companies_enriched ce ON ce.company_code = ca.company_code
LEFT JOIN financial_summary fs ON fs.company_id = ce.id
WHERE ca.is_active = true
