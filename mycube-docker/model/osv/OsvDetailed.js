cube(`OsvDetailed`, {
  sql: `SELECT * FROM history.osv_detailed`,
  
  title: 'ОСВ Детализация',
  description: 'Детализированные обороты по счетам бухгалтерского учета (сырые данные)',
  
  joins: {
    CompanyDirectory: {
      sql: `${CUBE}.inn = ${CompanyDirectory}.inn`,
      relationship: `belongsTo`
    }
  },
  
  measures: {
    count: {
      type: `count`,
      title: 'Количество записей'
    },
    
    totalOpeningDebit: {
      sql: `opening_debit`,
      type: `sum`,
      title: 'Входящее сальдо Дт',
      format: `currency`
    },
    
    totalOpeningCredit: {
      sql: `opening_credit`,
      type: `sum`,
      title: 'Входящее сальдо Кт',
      format: `currency`
    },
    
    totalTurnoverDebit: {
      sql: `turnover_debit`,
      type: `sum`,
      title: 'Оборот Дт',
      format: `currency`
    },
    
    totalTurnoverCredit: {
      sql: `turnover_credit`,
      type: `sum`,
      title: 'Оборот Кт',
      format: `currency`
    },
    
    totalClosingDebit: {
      sql: `closing_debit`,
      type: `sum`,
      title: 'Исходящее сальдо Дт',
      format: `currency`
    },
    
    totalClosingCredit: {
      sql: `closing_credit`,
      type: `sum`,
      title: 'Исходящее сальдо Кт',
      format: `currency`
    },
    
    netBalance: {
      sql: `(closing_debit - closing_credit)`,
      type: `sum`,
      title: 'Чистое сальдо (Дт - Кт)',
      format: `currency`
    },
    
    turnoverDifference: {
      sql: `(turnover_debit - turnover_credit)`,
      type: `sum`,
      title: 'Разница оборотов (Дт - Кт)',
      format: `currency`
    }
  },
  
  dimensions: {
    id: {
      sql: `id`,
      type: `number`,
      primaryKey: true
    },
    
    companyName: {
      sql: `company_name`,
      type: `string`,
      title: 'Компания'
    },
    
    inn: {
      sql: `inn`,
      type: `string`,
      title: 'ИНН'
    },
    
    period: {
      sql: `period`,
      type: `string`,
      title: 'Период'
    },
    
    account: {
      sql: `account`,
      type: `string`,
      title: 'Счет'
    },
    
    subkonto: {
      sql: `subkonto`,
      type: `string`,
      title: 'Субконто'
    },
    
    sourceFile: {
      sql: `source_file`,
      type: `string`,
      title: 'Исходный файл'
    },
    
    importDate: {
      sql: `import_date`,
      type: `time`,
      title: 'Дата импорта'
    },
    
    etlLoadedAt: {
      sql: `etl_loaded_at`,
      type: `time`,
      title: 'Загружено в ETL'
    }
  },
  
  segments: {
    hasDebitBalance: {
      sql: `${CUBE}.closing_debit > ${CUBE}.closing_credit`,
      title: 'С дебетовым сальдо'
    },
    
    hasCreditBalance: {
      sql: `${CUBE}.closing_credit > ${CUBE}.closing_debit`,
      title: 'С кредитовым сальдо'
    },
    
    activeAccounts: {
      sql: `${CUBE}.turnover_debit > 0 OR ${CUBE}.turnover_credit > 0`,
      title: 'Активные счета (с оборотами)'
    }
  }
});
