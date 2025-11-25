-- Fact table: Cost structure by company
-- Витрина структуры себестоимости по компаниям

{{ config(
    materialized='table',
    schema='analytics'
) }}

with enriched_costs as (
    select * from {{ ref('int_costs_enriched') }}
),

aggregated as (
    select
        company_code,
        company_name,
        inn,
        
        -- Иерархия затрат
        category_code,
        category_name,
        group_code,
        group_name,
        item_code,
        item_name,
        
        -- Тип счёта
        account_code,
        case account_code
            when '20' then 'Основное производство'
            when '26' then 'Общехозяйственные расходы'
            when '44' then 'Расходы на продажу'
            else 'Прочие'
        end as account_name,
        
        -- Агрегированные суммы
        sum(debit_amount) as total_debit,
        sum(credit_amount) as total_credit,
        sum(debit_amount - credit_amount) as net_amount,
        
        -- Количество записей
        count(*) as records_count,
        
        -- Статус маппинга
        mapping_status
        
    from enriched_costs
    group by
        company_code,
        company_name,
        inn,
        category_code,
        category_name,
        group_code,
        group_name,
        item_code,
        item_name,
        account_code,
        mapping_status
),

with_totals as (
    select
        *,
        -- Процент от общих затрат компании
        sum(total_debit) over (partition by company_code) as company_total_debit,
        total_debit * 100.0 / nullif(sum(total_debit) over (partition by company_code), 0) as pct_of_company_total,
        
        -- Процент от категории
        sum(total_debit) over (partition by company_code, category_code) as category_total_debit,
        total_debit * 100.0 / nullif(sum(total_debit) over (partition by company_code, category_code), 0) as pct_of_category,
        
        -- Процент от группы
        sum(total_debit) over (partition by company_code, group_code) as group_total_debit,
        total_debit * 100.0 / nullif(sum(total_debit) over (partition by company_code, group_code), 0) as pct_of_group
        
    from aggregated
)

select * from with_totals
order by company_code, category_code, group_code, item_code
