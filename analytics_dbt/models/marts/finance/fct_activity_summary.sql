{{
    config(
        materialized='table',
        schema='analytics'
    )
}}

WITH activity_summary AS (
    SELECT 
        activity_type,
        activity_sort_order,
        
        -- Количество компаний
        COUNT(*) as total_companies,
        COUNT(CASE WHEN profitability_status = 'Прибыльная' THEN 1 END) as profitable_companies,
        COUNT(CASE WHEN profitability_status = 'Убыточная' THEN 1 END) as loss_making_companies,
        COUNT(CASE WHEN profitability_status = 'Неактивная' THEN 1 END) as inactive_companies,
        
        -- Финансовые показатели
        SUM(revenue) as total_revenue,
        SUM(cost_of_sales) as total_cost_of_sales,
        SUM(selling_expenses) as total_selling_expenses,
        SUM(admin_expenses) as total_admin_expenses,
        SUM(total_expenses) as total_expenses,
        SUM(other_income) as total_other_income,
        SUM(other_expenses) as total_other_expenses,
        SUM(net_profit) as total_profit,
        
        -- Средние показатели
        AVG(CASE WHEN revenue > 0 THEN revenue END) as avg_revenue,
        AVG(CASE WHEN revenue > 0 THEN cost_to_revenue_pct END) as avg_cost_to_revenue_pct,
        AVG(CASE WHEN revenue > 0 THEN profit_margin_pct END) as avg_profit_margin_pct
        
    FROM {{ ref('fct_companies_by_activity') }}
    GROUP BY activity_type, activity_sort_order
)

SELECT 
    activity_type,
    activity_sort_order,
    
    total_companies,
    profitable_companies,
    loss_making_companies,
    inactive_companies,
    
    -- Финансовые показатели (округленные)
    ROUND(total_revenue::numeric, 2) as total_revenue,
    ROUND(total_cost_of_sales::numeric, 2) as total_cost_of_sales,
    ROUND(total_selling_expenses::numeric, 2) as total_selling_expenses,
    ROUND(total_admin_expenses::numeric, 2) as total_admin_expenses,
    ROUND(total_expenses::numeric, 2) as total_expenses,
    ROUND(total_other_income::numeric, 2) as total_other_income,
    ROUND(total_other_expenses::numeric, 2) as total_other_expenses,
    ROUND(total_profit::numeric, 2) as total_profit,
    
    -- Средние показатели
    ROUND(COALESCE(avg_revenue, 0)::numeric, 2) as avg_revenue_per_active_company,
    ROUND(COALESCE(avg_cost_to_revenue_pct, 0)::numeric, 2) as avg_cost_to_revenue_pct,
    ROUND(COALESCE(avg_profit_margin_pct, 0)::numeric, 2) as avg_profit_margin_pct,
    
    -- Расчетные метрики
    ROUND(
        CASE 
            WHEN total_revenue > 0 
            THEN (total_cost_of_sales / total_revenue * 100)::numeric
            ELSE 0 
        END, 
        2
    ) as cost_to_revenue_pct,
    
    ROUND(
        CASE 
            WHEN total_revenue > 0 
            THEN (total_profit / total_revenue * 100)::numeric
            ELSE 0 
        END, 
        2
    ) as profit_margin_pct,
    
    -- Доля в группе
    ROUND(
        (total_revenue / SUM(total_revenue) OVER () * 100)::numeric, 
        2
    ) as pct_of_group_revenue,
    
    ROUND(
        (total_profit / NULLIF(SUM(total_profit) OVER (), 0) * 100)::numeric, 
        2
    ) as pct_of_group_profit

FROM activity_summary
ORDER BY activity_sort_order, activity_type
