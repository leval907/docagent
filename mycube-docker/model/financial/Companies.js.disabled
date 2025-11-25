# Cube.js Companies model

cube(`Companies`, {
  sql: `
    SELECT 
      c.id,
      c.company_code,
      c.company_name,
      c.inn,
      c.ogrn,
      c.full_name,
      c.address,
      c.director_name,
      c.phone,
      c.status,
      c.registration_date,
      c.liquidation_date,
      c.primary_okved,
      c.enrichment_status,
      c.is_active
    FROM master.companies c
    WHERE c.is_active = TRUE
  `,
  
  title: "Компании группы",
  description: "Справочник компаний, входящих в группу",
  
  joins: {
    Okved: {
      relationship: `belongsTo`,
      sql: `${CUBE}.primary_okved = ${Okved}.code`
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
      title: "Код компании"
    },
    
    companyName: {
      sql: `company_name`,
      type: `string`,
      title: "Наименование"
    },
    
    inn: {
      sql: `inn`,
      type: `string`,
      title: "ИНН"
    },
    
    ogrn: {
      sql: `ogrn`,
      type: `string`,
      title: "ОГРН"
    },
    
    fullName: {
      sql: `full_name`,
      type: `string`,
      title: "Полное наименование"
    },
    
    address: {
      sql: `address`,
      type: `string`,
      title: "Адрес"
    },
    
    directorName: {
      sql: `director_name`,
      type: `string`,
      title: "Директор"
    },
    
    phone: {
      sql: `phone`,
      type: `string`,
      title: "Телефон"
    },
    
    status: {
      sql: `status`,
      type: `string`,
      title: "Статус",
      description: "Статус компании (Действующая, Ликвидирована и т.д.)"
    },
    
    registrationDate: {
      sql: `registration_date`,
      type: `time`,
      title: "Дата регистрации"
    },
    
    liquidationDate: {
      sql: `liquidation_date`,
      type: `time`,
      title: "Дата ликвидации"
    },
    
    primaryOkved: {
      sql: `primary_okved`,
      type: `string`,
      title: "Основной ОКВЭД"
    },
    
    enrichmentStatus: {
      sql: `enrichment_status`,
      type: `string`,
      title: "Статус обогащения"
    },
    
    isActive: {
      sql: `is_active`,
      type: `boolean`,
      title: "Активная"
    }
  },
  
  measures: {
    count: {
      type: `count`,
      title: "Количество компаний"
    }
  },
  
  segments: {
    activeCompanies: {
      sql: `${CUBE}.is_active = TRUE AND ${CUBE}.status = 'Действующая'`,
      title: "Действующие компании"
    },
    
    liquidated: {
      sql: `${CUBE}.liquidation_date IS NOT NULL`,
      title: "Ликвидированные"
    },
    
    enriched: {
      sql: `${CUBE}.enrichment_status = 'success'`,
      title: "С обогащенными данными"
    }
  }
});
