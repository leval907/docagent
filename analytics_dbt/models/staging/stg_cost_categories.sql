-- Staging model for cost categories
-- Справочник категорий затрат (постоянные/переменные)

with source as (
    select * from {{ source('master', 'cost_categories') }}
),

renamed as (
    select
        id as category_id,
        code as category_code,
        name_ru as category_name,
        name_en as category_name_en,
        sort_order,
        is_active,
        created_at
    from source
    where is_active = true
)

select * from renamed
