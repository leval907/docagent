cube(`CompanyDirectory`, {
  sql: `SELECT * FROM master.companies`,
  
  title: 'Справочник компаний',
  description: 'Мастер-данные компаний из схемы master',
  
  measures: {
    count: {
      type: `count`,
      title: 'Количество компаний'
    },
    
    activeCount: {
      sql: `CASE WHEN is_active = true THEN 1 END`,
      type: `count`,
      title: 'Активных компаний'
    }
  },
  
  dimensions: {
    id: {
      sql: `id`,
      type: `number`,
      primaryKey: true
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
    
    fullName: {
      sql: `full_name`,
      type: `string`,
      title: 'Полное наименование'
    },
    
    inn: {
      sql: `inn`,
      type: `string`,
      title: 'ИНН'
    },
    
    ogrn: {
      sql: `ogrn`,
      type: `string`,
      title: 'ОГРН'
    },
    
    address: {
      sql: `address`,
      type: `string`,
      title: 'Адрес'
    },
    
    directorName: {
      sql: `director_name`,
      type: `string`,
      title: 'Директор'
    },
    
    phone: {
      sql: `phone`,
      type: `string`,
      title: 'Телефон'
    },
    
    status: {
      sql: `status`,
      type: `string`,
      title: 'Статус'
    },
    
    okved: {
      sql: `okved`,
      type: `string`,
      title: 'ОКВЭД'
    },
    
    primaryOkved: {
      sql: `primary_okved`,
      type: `string`,
      title: 'Основной ОКВЭД'
    },
    
    isActive: {
      sql: `is_active`,
      type: `boolean`,
      title: 'Активна'
    },
    
    registrationDate: {
      sql: `registration_date`,
      type: `time`,
      title: 'Дата регистрации'
    },
    
    liquidationDate: {
      sql: `liquidation_date`,
      type: `time`,
      title: 'Дата ликвидации'
    },
    
    createdAt: {
      sql: `created_at`,
      type: `time`,
      title: 'Дата создания'
    },
    
    enrichedAt: {
      sql: `enriched_at`,
      type: `time`,
      title: 'Дата обогащения'
    },
    
    enrichmentStatus: {
      sql: `enrichment_status`,
      type: `string`,
      title: 'Статус обогащения'
    }
  },
  
  segments: {
    active: {
      sql: `${CUBE}.is_active = true`,
      title: 'Активные компании'
    },
    
    inactive: {
      sql: `${CUBE}.is_active = false`,
      title: 'Неактивные компании'
    },
    
    liquidated: {
      sql: `${CUBE}.liquidation_date IS NOT NULL`,
      title: 'Ликвидированные'
    },
    
    enriched: {
      sql: `${CUBE}.enrichment_status = 'completed'`,
      title: 'Обогащенные данные'
    }
  }
});
