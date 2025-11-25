cube(`ProfitLoss9M`, {
  sql: `SELECT * FROM analytics.profit_loss_9m`,
  
  title: 'Отчёт о финансовых результатах (9 месяцев)',
  description: 'ОФР сформирован из history.osv_9m_summary с использованием справочника счетов',
  
  joins: {
    CompanyDirectory: {
      sql: `${CUBE}.company_id = ${CompanyDirectory}.id`,
      relationship: `belongsTo`
    }
  },
  
  measures: {
    // Выручка (2110)
    totalRevenue: {
      sql: `revenue`,
      type: `sum`,
      title: 'Выручка',
      description: 'Счет 90.01 кредит',
      format: `currency`
    },
    
    // Себестоимость (2120)
    totalCostOfSales: {
      sql: `cost_of_sales`,
      type: `sum`,
      title: 'Себестоимость продаж',
      description: 'Счет 90.02 дебет',
      format: `currency`
    },
    
    // Валовая прибыль (2100)
    totalGrossProfit: {
      sql: `gross_profit`,
      type: `sum`,
      title: 'Валовая прибыль (убыток)',
      description: 'Выручка минус себестоимость',
      format: `currency`
    },
    
    // Коммерческие расходы (2210)
    totalSellingExpenses: {
      sql: `selling_expenses`,
      type: `sum`,
      title: 'Коммерческие расходы',
      description: 'Счет 90.07 дебет',
      format: `currency`
    },
    
    // Управленческие расходы (2220)
    totalAdminExpenses: {
      sql: `admin_expenses`,
      type: `sum`,
      title: 'Управленческие расходы',
      description: 'Счет 90.08 дебет',
      format: `currency`
    },
    
    // Прибыль от продаж (2200)
    totalOperatingProfit: {
      sql: `operating_profit`,
      type: `sum`,
      title: 'Прибыль (убыток) от продаж',
      description: 'Счет 90.09',
      format: `currency`
    },
    
    // Прочие доходы (2340)
    totalOtherIncome: {
      sql: `other_income`,
      type: `sum`,
      title: 'Прочие доходы',
      description: 'Счет 91.01 кредит',
      format: `currency`
    },
    
    // Прочие расходы (2350)
    totalOtherExpenses: {
      sql: `other_expenses`,
      type: `sum`,
      title: 'Прочие расходы',
      description: 'Счет 91.02 дебет',
      format: `currency`
    },
    
    // Прибыль до налогообложения (2300)
    totalProfitBeforeTax: {
      sql: `profit_before_tax`,
      type: `sum`,
      title: 'Прибыль (убыток) до налогообложения',
      description: 'Прибыль от продаж + прочие доходы - прочие расходы',
      format: `currency`
    },
    
    // Чистая прибыль (2400)
    totalNetProfit: {
      sql: `net_profit`,
      type: `sum`,
      title: 'Чистая прибыль (убыток)',
      description: 'Итоговый финансовый результат',
      format: `currency`
    },
    
    // Рентабельность
    grossMargin: {
      sql: `CASE WHEN ${CUBE}.revenue > 0 THEN (${CUBE}.gross_profit / ${CUBE}.revenue) * 100 ELSE 0 END`,
      type: `avg`,
      title: 'Рентабельность по валовой прибыли (%)',
      format: `percent`
    },
    
    operatingMargin: {
      sql: `CASE WHEN ${CUBE}.revenue > 0 THEN (${CUBE}.operating_profit / ${CUBE}.revenue) * 100 ELSE 0 END`,
      type: `avg`,
      title: 'Рентабельность продаж (%)',
      format: `percent`
    },
    
    netMargin: {
      sql: `CASE WHEN ${CUBE}.revenue > 0 THEN (${CUBE}.net_profit / ${CUBE}.revenue) * 100 ELSE 0 END`,
      type: `avg`,
      title: 'Рентабельность по чистой прибыли (%)',
      format: `percent`
    },
    
    count: {
      type: `count`,
      title: 'Количество компаний'
    }
  },
  
  dimensions: {
    id: {
      sql: `id`,
      type: `number`,
      primaryKey: true
    },
    
    companyId: {
      sql: `company_id`,
      type: `number`,
      title: 'ID компании'
    },
    
    companyCode: {
      sql: `company_code`,
      type: `string`,
      title: 'Код компании'
    },
    
    companyName: {
      sql: `company_name`,
      type: `string`,
      title: 'Название компании'
    },
    
    inn: {
      sql: `inn`,
      type: `string`,
      title: 'ИНН'
    }
  },
  
  segments: {
    profitable: {
      sql: `${CUBE}.net_profit > 0`,
      title: 'Прибыльные компании'
    },
    
    unprofitable: {
      sql: `${CUBE}.net_profit < 0`,
      title: 'Убыточные компании'
    },
    
    highRevenue: {
      sql: `${CUBE}.revenue > 100000000`,
      title: 'Выручка > 100 млн'
    },
    
    reasonable: {
      sql: `${CUBE}.is_reasonable = true`,
      title: 'Без аномалий в данных'
    },
    
    hasAnomalies: {
      sql: `${CUBE}.is_reasonable = false`,
      title: 'С аномальными прочими доходами'
    }
  }
});
