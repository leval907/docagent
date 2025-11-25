{{
  config(
    materialized='table',
    schema='analytics'
  )
}}

WITH pnl_data AS (
    SELECT 
        company_id,
        account_code,
        SUM(credit_turnover) as credit,
        SUM(debit_turnover) as debit
    FROM {{ ref('stg_osv_9m_summary') }}
    WHERE account_code IN ('90.01', '90.02', '90.07', '90.08', '91.01', '91.02', '99.02')
    GROUP BY company_id, account_code
),
companies AS (
    SELECT * FROM {{ ref('stg_companies') }}
)
SELECT
    c.company_id,
    c.company_code,
    c.company_name,
    c.inn,
    
    -- Revenue (90.01 Credit)
    COALESCE(SUM(CASE WHEN account_code = '90.01' THEN credit ELSE 0 END), 0) as revenue,
    
    -- Cost of Sales (90.02 Debit)
    COALESCE(SUM(CASE WHEN account_code = '90.02' THEN debit ELSE 0 END), 0) as cost_of_sales,
    
    -- Gross Profit (Revenue - Cost of Sales)
    COALESCE(SUM(CASE WHEN account_code = '90.01' THEN credit ELSE 0 END), 0) - 
    COALESCE(SUM(CASE WHEN account_code = '90.02' THEN debit ELSE 0 END), 0) as gross_profit,
    
    -- Selling Expenses (90.07 Debit)
    COALESCE(SUM(CASE WHEN account_code = '90.07' THEN debit ELSE 0 END), 0) as selling_expenses,
    
    -- Admin Expenses (90.08 Debit)
    COALESCE(SUM(CASE WHEN account_code = '90.08' THEN debit ELSE 0 END), 0) as admin_expenses,
    
    -- Operating Profit (Gross Profit - Selling - Admin)
    (COALESCE(SUM(CASE WHEN account_code = '90.01' THEN credit ELSE 0 END), 0) - 
     COALESCE(SUM(CASE WHEN account_code = '90.02' THEN debit ELSE 0 END), 0) -
     COALESCE(SUM(CASE WHEN account_code = '90.07' THEN debit ELSE 0 END), 0) -
     COALESCE(SUM(CASE WHEN account_code = '90.08' THEN debit ELSE 0 END), 0)) as operating_profit,
     
    -- Other Income (91.01 Credit)
    COALESCE(SUM(CASE WHEN account_code = '91.01' THEN credit ELSE 0 END), 0) as other_income,
    
    -- Other Expenses (91.02 Debit)
    COALESCE(SUM(CASE WHEN account_code = '91.02' THEN debit ELSE 0 END), 0) as other_expenses,
    
    -- Profit Before Tax (Operating + Other Income - Other Expenses)
    ((COALESCE(SUM(CASE WHEN account_code = '90.01' THEN credit ELSE 0 END), 0) - 
      COALESCE(SUM(CASE WHEN account_code = '90.02' THEN debit ELSE 0 END), 0) -
      COALESCE(SUM(CASE WHEN account_code = '90.07' THEN debit ELSE 0 END), 0) -
      COALESCE(SUM(CASE WHEN account_code = '90.08' THEN debit ELSE 0 END), 0)) +
     COALESCE(SUM(CASE WHEN account_code = '91.01' THEN credit ELSE 0 END), 0) -
     COALESCE(SUM(CASE WHEN account_code = '91.02' THEN debit ELSE 0 END), 0)) as profit_before_tax,
     
    -- Tax (99.02 Debit)
    COALESCE(SUM(CASE WHEN account_code = '99.02' THEN debit ELSE 0 END), 0) as tax_expenses,
    
    -- Net Profit (Profit Before Tax - Tax)
    (((COALESCE(SUM(CASE WHEN account_code = '90.01' THEN credit ELSE 0 END), 0) - 
       COALESCE(SUM(CASE WHEN account_code = '90.02' THEN debit ELSE 0 END), 0) -
       COALESCE(SUM(CASE WHEN account_code = '90.07' THEN debit ELSE 0 END), 0) -
       COALESCE(SUM(CASE WHEN account_code = '90.08' THEN debit ELSE 0 END), 0)) +
      COALESCE(SUM(CASE WHEN account_code = '91.01' THEN credit ELSE 0 END), 0) -
      COALESCE(SUM(CASE WHEN account_code = '91.02' THEN debit ELSE 0 END), 0)) -
     COALESCE(SUM(CASE WHEN account_code = '99.02' THEN debit ELSE 0 END), 0)) as net_profit,
     
     -- Metadata
     CURRENT_TIMESTAMP as calculated_at

FROM companies c
LEFT JOIN pnl_data p ON c.company_id = p.company_id
GROUP BY c.company_id, c.company_code, c.company_name, c.inn
