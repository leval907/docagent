{{
  config(
    materialized='view',
    schema='staging'
  )
}}

-- Staging модель для плана счетов
-- Источник: master.chart_of_accounts

with source as (
    select * from {{ source('master', 'chart_of_accounts') }}
),

renamed as (
    select
        id as account_id,
        account_code,
        account_name,
        account_level,
        parent_code,
        account_type,
        balance_type,
        is_active,
        subconto1,
        subconto2,
        subconto3,
        rsbu_type,
        balance_flag,
        pnl_flag,
        liquidity_group,
        maturity_group,
        wc_role,
        balance_equation_class,
        balance_mgmt_group,
        created_at
    from source
    where is_active = true  -- Только активные счета
)

select * from renamed
