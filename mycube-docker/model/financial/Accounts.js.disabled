# Cube.js configuration for financial analytics
# PostgreSQL connection to analytics database

cube(`Accounts`, {
  sql: `
    SELECT 
      id,
      account_code,
      account_name,
      account_level,
      parent_code,
      subconto1,
      subconto2,
      subconto3,
      rsbu_type,
      account_type,
      balance_type,
      balance_flag,
      pnl_flag,
      liquidity_group,
      maturity_group,
      wc_role,
      balance_mgmt_group,
      balance_equation_class,
      is_active
    FROM master.chart_of_accounts
    WHERE is_active = TRUE
  `,
  
  title: "План счетов",
  description: "Российский План счетов бухгалтерского учета с классификацией по типам, уровням аналитики и балансовым признакам",
  
  dimensions: {
    id: {
      sql: `id`,
      type: `number`,
      primaryKey: true
    },
    
    accountCode: {
      sql: `account_code`,
      type: `string`,
      title: "Код счета",
      description: "Код счета по российскому плану счетов (например: 01, 60.01, 62.02)"
    },
    
    accountName: {
      sql: `account_name`,
      type: `string`,
      title: "Наименование счета"
    },
    
    accountLevel: {
      sql: `account_level`,
      type: `number`,
      title: "Уровень иерархии",
      description: "1 - счет первого порядка, 2 - субсчет, 3 - детализация"
    },
    
    parentCode: {
      sql: `parent_code`,
      type: `string`,
      title: "Родительский счет"
    },
    
    // Аналитические измерения (субконто)
    subconto1: {
      sql: `subconto1`,
      type: `string`,
      title: "Субконто 1",
      description: "Первый уровень аналитики (Контрагенты, Номенклатура и т.д.)"
    },
    
    subconto2: {
      sql: `subconto2`,
      type: `string`,
      title: "Субконто 2"
    },
    
    subconto3: {
      sql: `subconto3`,
      type: `string`,
      title: "Субконто 3"
    },
    
    // Классификация по РСБУ
    rsbuType: {
      sql: `rsbu_type`,
      type: `string`,
      title: "Тип счета РСБУ",
      description: "А - активный, П - пассивный, АП - активно-пассивный"
    },
    
    accountType: {
      sql: `account_type`,
      type: `string`,
      title: "Тип счета"
    },
    
    balanceType: {
      sql: `balance_type`,
      type: `string`,
      title: "Тип баланса"
    },
    
    // Признаки
    balanceFlag: {
      sql: `balance_flag`,
      type: `boolean`,
      title: "Балансовый счет"
    },
    
    pnlFlag: {
      sql: `pnl_flag`,
      type: `boolean`,
      title: "Счет прибылей/убытков"
    },
    
    // Группы ликвидности
    liquidityGroup: {
      sql: `liquidity_group`,
      type: `string`,
      title: "Группа ликвидности",
      description: "A1-A4 (активы), P1-P4 (пассивы)"
    },
    
    maturityGroup: {
      sql: `maturity_group`,
      type: `string`,
      title: "Группа срочности"
    },
    
    wcRole: {
      sql: `wc_role`,
      type: `string`,
      title: "Роль в оборотном капитале"
    },
    
    balanceMgmtGroup: {
      sql: `balance_mgmt_group`,
      type: `string`,
      title: "Группа управленческого баланса"
    },
    
    balanceEquationClass: {
      sql: `balance_equation_class`,
      type: `string`,
      title: "Класс балансового уравнения"
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
      title: "Количество счетов"
    }
  },
  
  segments: {
    activeAccounts: {
      sql: `${CUBE}.is_active = TRUE`,
      title: "Активные счета"
    },
    
    balanceAccounts: {
      sql: `${CUBE}.balance_flag = TRUE`,
      title: "Балансовые счета"
    },
    
    pnlAccounts: {
      sql: `${CUBE}.pnl_flag = TRUE`,
      title: "Счета P&L"
    },
    
    highLiquidityAssets: {
      sql: `${CUBE}.liquidity_group = 'A1'`,
      title: "Высоколиквидные активы (A1)"
    },
    
    urgentLiabilities: {
      sql: `${CUBE}.liquidity_group = 'P1'`,
      title: "Наиболее срочные обязательства (P1)"
    }
  }
});
