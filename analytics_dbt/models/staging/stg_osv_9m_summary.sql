{{
  config(
    materialized='view',
    schema='staging'
  )
}}

-- Staging модель для OSV 9 месяцев
-- Источник: history.osv_9m_summary

with source as (
    select * from {{ source('history', 'osv_9m_summary') }}
),

renamed as (
    select
        id,
        company_id,
        period_date,
        account_code,
        analytic_1_type,
        analytic_1_code,
        analytic_2_type,
        analytic_2_code,
        debit_begin,
        credit_begin,
        debit_turnover,
        credit_turnover,
        debit_end,
        credit_end,
        detail_level,
        source_table,
        source_filename,
        loaded_at
    from source
)

select * from renamed
