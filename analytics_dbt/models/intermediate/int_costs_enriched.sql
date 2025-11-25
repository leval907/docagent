-- Intermediate model: enriched costs with full hierarchy
-- Обогащаем затраты справочниками: категория → группа → статья

with costs as (
    select * from {{ ref('stg_osv_9m_costs') }}
),

companies as (
    select * from {{ ref('stg_companies') }}
),

company_mapping as (
    select 
        source_name,
        target_company_id as company_id
    from {{ source('master', 'company_name_mapping') }}
),

cost_items as (
    select * from {{ ref('stg_cost_items') }}
),

cost_groups as (
    select * from {{ ref('stg_cost_groups') }}
),

cost_categories as (
    select * from {{ ref('stg_cost_categories') }}
),

-- Джойним затраты с компаниями через маппинг
costs_with_company as (
    select
        c.id as cost_id,
        c.filename,
        c.company_raw,
        comp.company_code,
        comp.company_name,
        comp.inn,
        comp.director_name,
        c.period as period_date,
        c.account_type as account_code,
        c.cost_item,
        c.amount_dt as debit_amount,
        c.amount_kt as credit_amount,
        c.filename as source_file
    from costs c
    left join company_mapping cm 
        on c.company_raw = cm.source_name
    left join companies comp 
        on cm.company_id = comp.company_id
),

-- Джойним со справочником статей (сначала по точному названию)
costs_with_items as (
    select
        cwc.*,
        ci.item_id,
        ci.item_code,
        ci.item_name,
        ci.category_id,
        ci.group_id,
        ci.extracted_code
    from costs_with_company cwc
    left join cost_items ci
        on cwc.cost_item = ci.item_name
),

final as (
    select
        cwi.cost_id,
        cwi.filename,
        cwi.company_raw,
        cwi.company_name,
        cwi.company_code,
        cwi.inn,
        cwi.director_name,
        cwi.period_date,
        cwi.account_code,
        cwi.cost_item as cost_item_original,
        cwi.debit_amount,
        cwi.credit_amount,
        
        -- Справочники
        cwi.item_id,
        cwi.item_code,
        cwi.item_name,
        
        cg.group_id,
        cg.group_code,
        cg.group_name,
        
        cc.category_id,
        cc.category_code,
        cc.category_name,
        
        -- Метрики
        case 
            when cwi.item_id is not null then 'matched'
            else 'unmatched'
        end as mapping_status
        
    from costs_with_items cwi
    left join cost_groups cg
        on cwi.group_id = cg.group_id
    left join cost_categories cc
        on cwi.category_id = cc.category_id
)

select * from final
