cube(`OsvSummary`, {
  sql: `SELECT * FROM history.osv_h1_summary`,
  
  title: 'ОСВ Сводка H1',
  description: 'Сводные обороты по счетам за первое полугодие - 6 компаний × 6 месяцев (сырые данные)',
  
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
    
    accountName: {
      sql: `account_name`,
      type: `string`,
      title: 'Название счета'
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
    }
  }
});
