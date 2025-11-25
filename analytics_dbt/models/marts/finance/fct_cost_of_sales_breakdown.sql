-- Fact table: Cost of Sales breakdown (раскрытие себестоимости 90.02)
-- Витрина структуры себестоимости продаж
-- Учитывает разную учётную политику:
--   - Большинство: счет 20 → 90.02
--   - БОС, Шиндяпин: счет 26 → 90.02

{{ config(
    materialized='table',
    schema='analytics'
) }}

with enriched_costs as (
    select * from {{ ref('int_costs_enriched') }}
),

-- Определяем учётную политику: какие компании списывают 26 на 90.02
-- (у них нет оборотов по счету 20 или 90.08)
company_policy as (
    select 
        company_code,
        case 
            -- Если есть обороты по 20, то это стандартная политика: 20→90.02, 26→90.08
            when sum(case when account_code = '20' and debit_amount > 0 then 1 else 0 end) > 0 
            then '20'
            -- Иначе берём 26 (БОС, Шиндяпин используют 26→90.02)
            else '26'
        end as cost_account
    from enriched_costs
    where account_code in ('20', '26')
    group by company_code
),

-- Берём затраты в зависимости от учётной политики
cost_of_sales as (
    select
        ec.company_code,
        ec.company_name,
        ec.inn,
        
        -- Иерархия затрат
        ec.category_code,
        ec.category_name,
        ec.group_code,
        ec.group_name,
        ec.item_code,
        ec.item_name,
        
        -- Дебетовые обороты = начисленные затраты
        sum(ec.debit_amount) as cost_accrued,
        sum(ec.credit_amount) as cost_written_off,
        sum(ec.debit_amount - ec.credit_amount) as cost_balance,
        
        -- Количество записей
        count(*) as records_count,
        
        -- Статус маппинга
        ec.mapping_status,
        
        -- Учётная политика
        cp.cost_account as accounting_policy
        
    from enriched_costs ec
    inner join company_policy cp 
        on ec.company_code = cp.company_code
        and ec.account_code = cp.cost_account
    group by
        ec.company_code,
        ec.company_name,
        ec.inn,
        ec.category_code,
        ec.category_name,
        ec.group_code,
        ec.group_name,
        ec.item_code,
        ec.item_name,
        ec.mapping_status,
        cp.cost_account
),

with_totals as (
    select
        *,
        -- Процент от общих начисленных затрат компании
        sum(cost_accrued) over (partition by company_code) as company_total_accrued,
        cost_accrued * 100.0 / nullif(sum(cost_accrued) over (partition by company_code), 0) as pct_of_company_accrued,
        
        -- Процент от категории
        sum(cost_accrued) over (partition by company_code, category_code) as category_total_accrued,
        cost_accrued * 100.0 / nullif(sum(cost_accrued) over (partition by company_code, category_code), 0) as pct_of_category,
        
        -- Процент от группы
        sum(cost_accrued) over (partition by company_code, group_code) as group_total_accrued,
        cost_accrued * 100.0 / nullif(sum(cost_accrued) over (partition by company_code, group_code), 0) as pct_of_group
        
    from cost_of_sales
)

select * from with_totals
order by company_code, category_code, group_code, item_code
