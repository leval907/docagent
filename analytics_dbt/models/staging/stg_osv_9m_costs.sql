{{
  config(
    materialized='view',
    schema='staging'
  )
}}

-- Staging модель для структуры затрат за 9 месяцев
-- Источник: history.osv_9m_costs

with source as (
    select * from {{ source('history', 'osv_9m_costs') }}
),

renamed as (
    select
        id,
        filename,
        company_raw,
        period,
        account_type,
        cost_item,
        amount_dt,
        amount_kt,
        etl_loaded_at
    from source
)

select * from renamed
