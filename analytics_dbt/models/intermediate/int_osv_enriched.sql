{{
  config(
    materialized='view',
    schema='intermediate'
  )
}}

-- Обогащение OSV 9м данными из справочников
-- Добавляем информацию о компании и счёте

with osv as (
    select * from {{ ref('stg_osv_9m_summary') }}
),

companies as (
    select * from {{ ref('stg_companies') }}
),

accounts as (
    select * from {{ ref('stg_chart_of_accounts') }}
),

enriched as (
    select
        -- OSV данные
        osv.id,
        osv.period_date,
        osv.debit_begin,
        osv.credit_begin,
        osv.debit_turnover,
        osv.credit_turnover,
        osv.debit_end,
        osv.credit_end,
        osv.detail_level,
        osv.analytic_1_type,
        osv.analytic_1_code,
        osv.analytic_2_type,
        osv.analytic_2_code,
        
        -- Информация о компании
        companies.company_id,
        companies.company_code,
        companies.company_name,
        companies.inn,
        companies.ogrn,
        companies.director_name,
        companies.status as company_status,
        
        -- Информация о счёте
        accounts.account_id,
        osv.account_code,
        accounts.account_name,
        accounts.account_level,
        accounts.parent_code,
        accounts.account_type,
        accounts.balance_type,
        accounts.pnl_flag,
        accounts.balance_flag,
        accounts.rsbu_type,
        
        -- Метаданные
        osv.source_table,
        osv.source_filename,
        osv.loaded_at
        
    from osv
    left join companies on osv.company_id = companies.company_id
    left join accounts on osv.account_code = accounts.account_code
)

select * from enriched
