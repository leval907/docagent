{{
  config(
    materialized='table',
    schema='analytics'
  )
}}

with companies as (
    select * from {{ ref('stg_companies') }}
),

overrides as (
    select * from {{ ref('company_activity_overrides') }}
)

select
    c.company_id,
    c.company_code,
    c.company_name,
    c.inn,
    c.primary_okved,
    
    -- Приоритет фактической деятельности над ОКВЭД
    coalesce(o.actual_activity, c.primary_okved) as activity_type,
    
    -- Роль компании (Asset Holder, Operating, SSC, etc.)
    -- Если нет в overrides, определяем по умолчанию как 'Unclassified'
    coalesce(o.company_role, 'Unclassified') as company_role,
    
    c.is_active,
    c.status

from companies c
left join overrides o on c.company_code = o.company_code
