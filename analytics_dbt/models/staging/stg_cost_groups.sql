-- Staging model for cost groups
-- Справочник групп затрат (амортизация, IT, аренда и т.д.)

with source as (
    select * from {{ source('master', 'cost_groups') }}
),

renamed as (
    select
        id as group_id,
        group_code,
        name_ru as group_name,
        name_en as group_name_en,
        category_id,
        sort_order,
        is_active,
        created_at
    from source
    where is_active = true
)

select * from renamed
