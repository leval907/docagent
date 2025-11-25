{{
  config(
    materialized='view',
    schema='staging'
  )
}}

-- Staging модель для справочника организаций
-- Источник: master.companies

with source as (
    select * from {{ source('master', 'companies') }}
),

renamed as (
    select
        id as company_id,
        company_code,
        company_name,
        full_name,
        inn,
        ogrn,
        address,
        director_name,
        phone,
        status,
        registration_date,
        liquidation_date,
        okved,
        primary_okved,
        is_active,
        enrichment_status,
        enriched_at,
        created_at
    from source
    where is_active = true  -- Только активные компании
)

select * from renamed
