-- Staging model for cost items
-- Справочник статей затрат с извлечением кода для джойна

with source as (
    select * from {{ source('master', 'cost_items') }}
),

renamed as (
    select
        id as item_id,
        code as item_code,
        name_ru as item_name,
        name_en as item_name_en,
        category_id,
        group_id,
        sort_order,
        is_active,
        created_at,
        -- Извлекаем код из названия (например, "(409)" -> "409")
        substring(name_ru from '\(([0-9]+)\)') as extracted_code
    from source
    where is_active = true
)

select * from renamed
