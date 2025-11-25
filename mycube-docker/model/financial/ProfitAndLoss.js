cube(`ProfitAndLoss`, {
  sql: `SELECT * FROM analytics.profit_v`,
  
  title: "Profit & Loss (P&L)",
  description: "AI-generated P&L statements from OSV data via GigaChat agent",
  
  measures: {
    count: {
      type: `count`,
      title: "Report Count",
      description: "Number of P&L reports generated"
    },
    
    // Revenue metrics
    totalRevenue: {
      sql: `"Revenue"`,
      type: `sum`,
      title: "Total Revenue",
      description: "Sum of revenue across all companies",
      format: `currency`
    },
    
    avgRevenue: {
      sql: `"Revenue"`,
      type: `avg`,
      title: "Average Revenue",
      description: "Average revenue per company",
      format: `currency`
    },
    
    // Cost metrics
    totalCostOfGoods: {
      sql: `"Cost of Goods"`,
      type: `sum`,
      title: "Total Cost of Goods Sold",
      description: "Total COGS across all companies",
      format: `currency`
    },
    
    totalOverheads: {
      sql: `"Overheads"`,
      type: `sum`,
      title: "Total Overheads",
      description: "Total overhead expenses",
      format: `currency`
    },
    
    // Profitability metrics
    grossProfit: {
      sql: `"Revenue" - "Cost of Goods"`,
      type: `sum`,
      title: "Gross Profit",
      description: "Revenue minus Cost of Goods Sold",
      format: `currency`
    },
    
    grossProfitMargin: {
      sql: `CASE 
        WHEN SUM("Revenue") > 0 
        THEN (SUM("Revenue" - "Cost of Goods") / SUM("Revenue")) * 100 
        ELSE 0 
      END`,
      type: `number`,
      title: "Gross Profit Margin %",
      description: "Gross profit as percentage of revenue",
      format: `percent`
    },
    
    operatingProfit: {
      sql: `"Revenue" - "Cost of Goods" - "Overheads"`,
      type: `sum`,
      title: "Operating Profit (EBIT)",
      description: "Earnings Before Interest and Taxes",
      format: `currency`
    },
    
    operatingMargin: {
      sql: `CASE 
        WHEN SUM("Revenue") > 0 
        THEN (SUM("Revenue" - "Cost of Goods" - "Overheads") / SUM("Revenue")) * 100 
        ELSE 0 
      END`,
      type: `number`,
      title: "Operating Margin %",
      description: "Operating profit as percentage of revenue",
      format: `percent`
    },
    
    netProfit: {
      sql: `"Revenue" - "Cost of Goods" - "Overheads" - "Interest Paid" - "Tax Paid"`,
      type: `sum`,
      title: "Net Profit",
      description: "Bottom line profit after all expenses",
      format: `currency`
    },
    
    netMargin: {
      sql: `CASE 
        WHEN SUM("Revenue") > 0 
        THEN (SUM("Revenue" - "Cost of Goods" - "Overheads" - "Interest Paid" - "Tax Paid") / SUM("Revenue")) * 100 
        ELSE 0 
      END`,
      type: `number`,
      title: "Net Profit Margin %",
      description: "Net profit as percentage of revenue",
      format: `percent`
    },
    
    // Other expense metrics
    totalLeasing: {
      sql: `"Leasing"`,
      type: `sum`,
      title: "Total Leasing",
      format: `currency`
    },
    
    totalInterest: {
      sql: `"Interest Paid"`,
      type: `sum`,
      title: "Total Interest Paid",
      format: `currency`
    },
    
    totalDepreciation: {
      sql: `"Depreciation & Amortisation"`,
      type: `sum`,
      title: "Total Depreciation & Amortization",
      format: `currency`
    },
    
    totalTax: {
      sql: `"Tax Paid"`,
      type: `sum`,
      title: "Total Tax Paid",
      format: `currency`
    },
    
    totalDividends: {
      sql: `"Dividends Paid"`,
      type: `sum`,
      title: "Total Dividends Paid",
      format: `currency`
    },
    
    extraordinaryIncome: {
      sql: `"Extraordinary Income/Expenses"`,
      type: `sum`,
      title: "Extraordinary Income/Expenses",
      format: `currency`
    },
    
    // EBITDA
    ebitda: {
      sql: `"Revenue" - "Cost of Goods" - "Overheads" + "Depreciation & Amortisation"`,
      type: `sum`,
      title: "EBITDA",
      description: "Earnings Before Interest, Taxes, Depreciation and Amortization",
      format: `currency`
    },
    
    ebitdaMargin: {
      sql: `CASE 
        WHEN SUM("Revenue") > 0 
        THEN (SUM("Revenue" - "Cost of Goods" - "Overheads" + "Depreciation & Amortisation") / SUM("Revenue")) * 100 
        ELSE 0 
      END`,
      type: `number`,
      title: "EBITDA Margin %",
      format: `percent`
    }
  },
  
  dimensions: {
    id: {
      sql: `id`,
      type: `number`,
      primaryKey: true,
      shown: false
    },
    
    companyCode: {
      sql: `company_code`,
      type: `string`,
      title: "Company Code"
    },
    
    companyName: {
      sql: `company_name`,
      type: `string`,
      title: "Company Name"
    },
    
    // Individual values as dimensions for filtering
    revenue: {
      sql: `"Revenue"`,
      type: `number`,
      title: "Revenue",
      format: `currency`
    },
    
    costOfGoods: {
      sql: `"Cost of Goods"`,
      type: `number`,
      title: "Cost of Goods",
      format: `currency`
    },
    
    overheads: {
      sql: `"Overheads"`,
      type: `number`,
      title: "Overheads",
      format: `currency`
    }
  },
  
  segments: {
    profitable: {
      sql: `"Revenue" - "Cost of Goods" - "Overheads" - "Interest Paid" - "Tax Paid" > 0`,
      title: "Profitable Companies",
      description: "Companies with positive net profit"
    },
    
    unprofitable: {
      sql: `"Revenue" - "Cost of Goods" - "Overheads" - "Interest Paid" - "Tax Paid" <= 0`,
      title: "Unprofitable Companies",
      description: "Companies with negative net profit"
    },
    
    highMargin: {
      sql: `CASE 
        WHEN "Revenue" > 0 
        THEN ("Revenue" - "Cost of Goods") / "Revenue" > 0.3 
        ELSE false 
      END`,
      title: "High Margin Companies",
      description: "Companies with gross margin > 30%"
    },
    
    hasInterest: {
      sql: `"Interest Paid" > 0`,
      title: "Companies with Debt",
      description: "Companies paying interest (have debt)"
    },
    
    paysDividends: {
      sql: `"Dividends Paid" > 0`,
      title: "Dividend-Paying Companies",
      description: "Companies that paid dividends"
    }
  }
});
