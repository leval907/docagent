# Cube.js RSBU Codes model

cube(`RsbuCodes`, {
  sql: `
    SELECT 
      id,
      code,
      name,
      form,
      section,
      row_type,
      is_calculated,
      is_active
    FROM master.rsbu_codes
    WHERE is_active = TRUE
  `,
  
  title: "Коды отчетности РСБУ",
  description: "Справочник кодов строк бухгалтерской отчетности (Баланс, ОФР, ОДК, ОИК)",
  
  dimensions: {
    id: {
      sql: `id`,
      type: `number`,
      primaryKey: true
    },
    
    code: {
      sql: `code`,
      type: `number`,
      title: "Код строки",
      description: "Код строки отчетности (1100, 1150, 2110 и т.д.)"
    },
    
    name: {
      sql: `name`,
      type: `string`,
      title: "Наименование строки"
    },
    
    form: {
      sql: `form`,
      type: `string`,
      title: "Форма отчетности",
      description: "БАЛАНС, ОФР, ОДК, ОИК, ОЦИ"
    },
    
    section: {
      sql: `section`,
      type: `string`,
      title: "Раздел",
      description: "АКТИВ, ПАССИВ, КАПИТАЛ, ДЕНЕЖНЫЕ ПОТОКИ и т.д."
    },
    
    rowType: {
      sql: `row_type`,
      type: `string`,
      title: "Тип строки",
      description: "СТАТЬЯ, ИТОГО, РЕЗУЛЬТАТ, САЛЬДО"
    },
    
    isCalculated: {
      sql: `is_calculated`,
      type: `boolean`,
      title: "Расчетная строка",
      description: "Автоматически рассчитываемая строка (итоги, сальдо)"
    },
    
    isActive: {
      sql: `is_active`,
      type: `boolean`,
      title: "Активный"
    }
  },
  
  measures: {
    count: {
      type: `count`,
      title: "Количество кодов"
    }
  },
  
  segments: {
    balance: {
      sql: `${CUBE}.form = 'БАЛАНС'`,
      title: "Бухгалтерский баланс"
    },
    
    incomeStatement: {
      sql: `${CUBE}.form = 'ОФР'`,
      title: "Отчет о финансовых результатах"
    },
    
    cashFlow: {
      sql: `${CUBE}.form = 'ОДК'`,
      title: "Отчет о движении денежных средств"
    },
    
    equity: {
      sql: `${CUBE}.form = 'ОИК'`,
      title: "Отчет об изменениях капитала"
    },
    
    detailLines: {
      sql: `${CUBE}.is_calculated = FALSE`,
      title: "Детальные строки"
    },
    
    totalLines: {
      sql: `${CUBE}.is_calculated = TRUE`,
      title: "Итоговые строки"
    }
  }
});
