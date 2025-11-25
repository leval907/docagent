{{
  config(
    materialized='table',
    schema='analytics'
  )
}}

with osv as (
    select * from {{ ref('stg_osv_9m_summary') }}
),

companies as (
    select * from {{ ref('dim_companies') }}
),

asset_balances as (
    select
        company_id,
        
        -- Основные средства (01)
        sum(case when account_code like '01%' then debit_end else 0 end) as os_initial_cost,
        
        -- Доходные вложения (03)
        sum(case when account_code like '03%' then debit_end else 0 end) as income_investments,
        
        -- Вложения во внеоборотные активы (08)
        sum(case when account_code like '08%' then debit_end else 0 end) as capex_investments,
        
        -- Амортизация (02)
        sum(case when account_code like '02%' then credit_end else 0 end) as depreciation_accumulated

    from osv
    group by 1
)

select
    c.company_code,
    c.company_name,
    c.company_role,
    c.activity_type,
    
    coalesce(a.os_initial_cost, 0) as os_initial_cost,
    coalesce(a.income_investments, 0) as income_investments,
    coalesce(a.capex_investments, 0) as capex_investments,
    coalesce(a.depreciation_accumulated, 0) as depreciation_accumulated,
    
    -- Полная стоимость активов (01 + 03 + 08)
    (coalesce(a.os_initial_cost, 0) + coalesce(a.income_investments, 0) + coalesce(a.capex_investments, 0)) as total_assets_cost,
    
    -- Остаточная стоимость (Net Book Value)
    ((coalesce(a.os_initial_cost, 0) + coalesce(a.income_investments, 0)) - coalesce(a.depreciation_accumulated, 0)) as net_book_value,
    
    -- Степень износа (%)
    case 
        when (coalesce(a.os_initial_cost, 0) + coalesce(a.income_investments, 0)) > 0 
        then (coalesce(a.depreciation_accumulated, 0) / (coalesce(a.os_initial_cost, 0) + coalesce(a.income_investments, 0))) * 100
        else 0 
    end as wear_percentage,
    
    -- Флаг критического износа (>70%)
    case 
        when (coalesce(a.os_initial_cost, 0) + coalesce(a.income_investments, 0)) > 0 
             and (coalesce(a.depreciation_accumulated, 0) / (coalesce(a.os_initial_cost, 0) + coalesce(a.income_investments, 0))) > 0.7
        then true
        else false
    end as is_critical_wear

from companies c
left join asset_balances a on c.company_id = a.company_id
where c.is_active = true
