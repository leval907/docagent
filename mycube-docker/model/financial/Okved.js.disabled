# Cube.js OKVED classifier model

cube(`Okved`, {
  sql: `
    SELECT 
      id,
      code,
      parent_code,
      section,
      name,
      comment,
      level,
      is_active
    FROM master.okved
    WHERE is_active = TRUE
  `,
  
  title: "Классификатор ОКВЭД 2",
  description: "Общероссийский классификатор видов экономической деятельности",
  
  dimensions: {
    id: {
      sql: `id`,
      type: `number`,
      primaryKey: true
    },
    
    code: {
      sql: `code`,
      type: `string`,
      title: "Код ОКВЭД"
    },
    
    parentCode: {
      sql: `parent_code`,
      type: `string`,
      title: "Родительский код"
    },
    
    section: {
      sql: `section`,
      type: `string`,
      title: "Раздел",
      description: "Раздел ОКВЭД (A-U)"
    },
    
    name: {
      sql: `name`,
      type: `string`,
      title: "Наименование"
    },
    
    comment: {
      sql: `comment`,
      type: `string`,
      title: "Комментарий"
    },
    
    level: {
      sql: `level`,
      type: `number`,
      title: "Уровень иерархии",
      description: "1-раздел, 2-класс, 3-подкласс, 4-группа, 5-подгруппа, 6-вид"
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
    sections: {
      sql: `${CUBE}.level = 1`,
      title: "Разделы (A-U)"
    },
    
    classes: {
      sql: `${CUBE}.level = 2`,
      title: "Классы (XX)"
    },
    
    detailedCodes: {
      sql: `${CUBE}.level >= 4`,
      title: "Детальные коды"
    },
    
    itSector: {
      sql: `${CUBE}.section = 'J'`,
      title: "IT и связь (раздел J)"
    },
    
    realEstate: {
      sql: `${CUBE}.section = 'L'`,
      title: "Недвижимость (раздел L)"
    },
    
    professionalServices: {
      sql: `${CUBE}.section = 'M'`,
      title: "Профессиональные услуги (раздел M)"
    }
  }
});
