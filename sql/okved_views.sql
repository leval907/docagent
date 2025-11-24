-- Представление для получения полного пути ОКВЭД
-- Пример: 62.01 → 62.0 → 62 → J → путь и все названия

CREATE OR REPLACE VIEW master.v_okved_hierarchy AS
WITH RECURSIVE okved_path AS (
    -- Базовый уровень (корни)
    SELECT 
        o.id,
        o.code,
        o.parent_code,
        o.section,
        o.name,
        o.comment,
        o.level,
        o.code::TEXT AS path_codes,
        o.name::TEXT AS path_names,
        1 AS depth
    FROM master.okved o
    WHERE o.parent_code IS NULL OR o.parent_code = ''
    
    UNION ALL
    
    -- Рекурсия вниз по иерархии
    SELECT 
        o.id,
        o.code,
        o.parent_code,
        o.section,
        o.name,
        o.comment,
        o.level,
        (op.path_codes || ' → ' || o.code)::TEXT AS path_codes,
        (op.path_names || ' → ' || o.name)::TEXT AS path_names,
        op.depth + 1 AS depth
    FROM master.okved o
    INNER JOIN okved_path op ON o.parent_code = op.code
    WHERE o.parent_code IS NOT NULL AND o.parent_code != ''
)
SELECT 
    id,
    code,
    parent_code,
    section,
    name,
    comment,
    level,
    path_codes,
    path_names,
    depth,
    -- Извлечение раздела (первый элемент пути)
    SPLIT_PART(path_codes, ' → ', 1) AS root_section,
    -- Извлечение класса (второй элемент, если есть)
    CASE 
        WHEN depth >= 2 THEN SPLIT_PART(path_codes, ' → ', 2)
        ELSE NULL 
    END AS class_code
FROM okved_path;

COMMENT ON VIEW master.v_okved_hierarchy IS 
'Иерархическое представление ОКВЭД с полными путями от раздела до конкретного кода';

-- Представление компаний с их ОКВЭД и расшифровками
CREATE OR REPLACE VIEW master.v_companies_with_okved AS
SELECT 
    c.id AS company_id,
    c.company_name,
    c.inn,
    c.primary_okved,
    o_main.name AS primary_okved_name,
    o_main.section AS primary_section,
    o_main.path_codes AS primary_path,
    -- Дополнительные ОКВЭД (массивом)
    ARRAY_AGG(
        DISTINCT co.okved_code ORDER BY co.okved_code
    ) FILTER (WHERE co.okved_code IS NOT NULL) AS additional_okved_codes,
    ARRAY_AGG(
        DISTINCT o_add.name ORDER BY o_add.name
    ) FILTER (WHERE o_add.name IS NOT NULL) AS additional_okved_names
FROM master.companies c
LEFT JOIN master.v_okved_hierarchy o_main 
    ON c.primary_okved = o_main.code
LEFT JOIN master.companies_okved co 
    ON c.id = co.company_id AND co.is_primary = FALSE
LEFT JOIN master.okved o_add 
    ON co.okved_code = o_add.code
GROUP BY 
    c.id, c.company_name, c.inn, c.primary_okved,
    o_main.name, o_main.section, o_main.path_codes;

COMMENT ON VIEW master.v_companies_with_okved IS 
'Компании с расшифровкой основного и дополнительных кодов ОКВЭД';

-- Представление контрагентов с их ОКВЭД
CREATE OR REPLACE VIEW master.v_counterparties_with_okved AS
SELECT 
    cp.id AS counterparty_id,
    cp.counterparty_name,
    cp.inn,
    cp.primary_okved,
    o_main.name AS primary_okved_name,
    o_main.section AS primary_section,
    o_main.path_codes AS primary_path,
    -- Дополнительные ОКВЭД
    ARRAY_AGG(
        DISTINCT cpo.okved_code ORDER BY cpo.okved_code
    ) FILTER (WHERE cpo.okved_code IS NOT NULL) AS additional_okved_codes,
    ARRAY_AGG(
        DISTINCT o_add.name ORDER BY o_add.name
    ) FILTER (WHERE o_add.name IS NOT NULL) AS additional_okved_names
FROM master.counterparties cp
LEFT JOIN master.v_okved_hierarchy o_main 
    ON cp.primary_okved = o_main.code
LEFT JOIN master.counterparties_okved cpo 
    ON cp.id = cpo.counterparty_id AND cpo.is_primary = FALSE
LEFT JOIN master.okved o_add 
    ON cpo.okved_code = o_add.code
GROUP BY 
    cp.id, cp.counterparty_name, cp.inn, cp.primary_okved,
    o_main.name, o_main.section, o_main.path_codes;

COMMENT ON VIEW master.v_counterparties_with_okved IS 
'Контрагенты с расшифровкой основного и дополнительных кодов ОКВЭД';

-- Примеры использования:

-- 1. Найти все компании в IT-секторе (раздел J, класс 62)
-- SELECT * FROM master.v_companies_with_okved 
-- WHERE primary_section = 'J' AND primary_okved LIKE '62%';

-- 2. Полная иерархия для конкретного кода
-- SELECT * FROM master.v_okved_hierarchy WHERE code = '62.01';

-- 3. Все подкоды раздела
-- SELECT code, name, level FROM master.okved 
-- WHERE section = 'J' ORDER BY code;
