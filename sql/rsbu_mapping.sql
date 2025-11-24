-- Таблица маппинга счетов на строки отчетности РСБУ
-- Связывает план счетов (chart_of_accounts) с кодами отчетности (rsbu_codes)

CREATE TABLE IF NOT EXISTS master.account_rsbu_mapping (
    id SERIAL PRIMARY KEY,
    account_id INTEGER NOT NULL REFERENCES master.chart_of_accounts(id) ON DELETE CASCADE,
    rsbu_code INTEGER NOT NULL REFERENCES master.rsbu_codes(code) ON DELETE CASCADE,
    form VARCHAR(50) NOT NULL,              -- БАЛАНС, ОФР, ОДК, ОИК
    direction VARCHAR(10),                  -- DEBIT, CREDIT (для ОФР/ОДК)
    is_primary BOOLEAN DEFAULT TRUE,        -- Основное соответствие
    priority INTEGER DEFAULT 1,             -- Приоритет (для множественных маппингов)
    comment TEXT,                           -- Пояснение маппинга
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(account_id, rsbu_code, direction)
);

-- Индексы
CREATE INDEX IF NOT EXISTS idx_account_rsbu_account ON master.account_rsbu_mapping(account_id);
CREATE INDEX IF NOT EXISTS idx_account_rsbu_code ON master.account_rsbu_mapping(rsbu_code);
CREATE INDEX IF NOT EXISTS idx_account_rsbu_form ON master.account_rsbu_mapping(form);

-- Комментарии
COMMENT ON TABLE master.account_rsbu_mapping IS 
'Маппинг счетов плана счетов на строки бухгалтерской отчетности РСБУ';
COMMENT ON COLUMN master.account_rsbu_mapping.direction IS 
'Направление для ОФР/ОДК: DEBIT (дебет увеличивает показатель), CREDIT (кредит увеличивает)';
COMMENT ON COLUMN master.account_rsbu_mapping.is_primary IS 
'Основное соответствие (если счет попадает в несколько строк)';
COMMENT ON COLUMN master.account_rsbu_mapping.priority IS 
'Приоритет маппинга (1 - высший) для разрешения конфликтов';

-- Представление для удобной работы с маппингом
CREATE OR REPLACE VIEW master.v_account_rsbu_mapping AS
SELECT 
    m.id AS mapping_id,
    ca.id AS account_id,
    ca.account_code,
    ca.account_name,
    ca.balance_flag,
    ca.pnl_flag,
    r.code AS rsbu_code,
    r.name AS rsbu_name,
    r.form AS rsbu_form,
    r.section AS rsbu_section,
    r.row_type AS rsbu_row_type,
    r.is_calculated AS rsbu_is_calculated,
    m.direction,
    m.is_primary,
    m.priority,
    m.comment
FROM master.account_rsbu_mapping m
INNER JOIN master.chart_of_accounts ca ON m.account_id = ca.id
INNER JOIN master.rsbu_codes r ON m.rsbu_code = r.code
ORDER BY ca.account_code, r.code;

COMMENT ON VIEW master.v_account_rsbu_mapping IS 
'Представление маппинга счетов на строки РСБУ с полными расшифровками';

-- Представление: счета без маппинга
CREATE OR REPLACE VIEW master.v_accounts_without_rsbu AS
SELECT 
    ca.id,
    ca.account_code,
    ca.account_name,
    ca.balance_flag,
    ca.pnl_flag,
    ca.liquidity_group,
    ca.rsbu_type
FROM master.chart_of_accounts ca
LEFT JOIN master.account_rsbu_mapping m ON ca.id = m.account_id
WHERE m.id IS NULL
AND ca.is_active = TRUE
ORDER BY ca.account_code;

COMMENT ON VIEW master.v_accounts_without_rsbu IS 
'Счета без маппинга на строки РСБУ (требуют настройки)';

-- Представление: строки РСБУ без счетов
CREATE OR REPLACE VIEW master.v_rsbu_without_accounts AS
SELECT 
    r.code,
    r.name,
    r.form,
    r.section,
    r.row_type,
    r.is_calculated
FROM master.rsbu_codes r
LEFT JOIN master.account_rsbu_mapping m ON r.code = m.rsbu_code
WHERE m.id IS NULL
AND r.is_calculated = FALSE  -- Только детальные строки (не итоги)
ORDER BY r.code;

COMMENT ON VIEW master.v_rsbu_without_accounts IS 
'Строки РСБУ без привязанных счетов (требуют маппинга)';

-- ==================================================================================
-- ПРИМЕРЫ БАЗОВОГО МАППИНГА (стартовая точка для настройки)
-- ==================================================================================

-- БАЛАНС: Актив

-- 1. Внеоборотные активы
-- 04 "Нематериальные активы" → 1110
INSERT INTO master.account_rsbu_mapping (account_id, rsbu_code, form, comment)
SELECT ca.id, 1110, 'БАЛАНС', 'НМА'
FROM master.chart_of_accounts ca
WHERE ca.account_code LIKE '04%' 
AND NOT EXISTS (
    SELECT 1 FROM master.account_rsbu_mapping m 
    WHERE m.account_id = ca.id AND m.rsbu_code = 1110
);

-- 01 "Основные средства" → 1150
INSERT INTO master.account_rsbu_mapping (account_id, rsbu_code, form, comment)
SELECT ca.id, 1150, 'БАЛАНС', 'Основные средства'
FROM master.chart_of_accounts ca
WHERE ca.account_code LIKE '01%' 
AND NOT EXISTS (
    SELECT 1 FROM master.account_rsbu_mapping m 
    WHERE m.account_id = ca.id AND m.rsbu_code = 1150
);

-- 58 "Финансовые вложения" (долгосрочные) → 1170
INSERT INTO master.account_rsbu_mapping (account_id, rsbu_code, form, comment)
SELECT ca.id, 1170, 'БАЛАНС', 'Финансовые вложения долгосрочные'
FROM master.chart_of_accounts ca
WHERE ca.account_code LIKE '58%' AND ca.liquidity_group IN ('A3', 'A4')
AND NOT EXISTS (
    SELECT 1 FROM master.account_rsbu_mapping m 
    WHERE m.account_id = ca.id AND m.rsbu_code = 1170
);

-- 2. Оборотные активы

-- 10 "Материалы" → 1210
INSERT INTO master.account_rsbu_mapping (account_id, rsbu_code, form, comment)
SELECT ca.id, 1210, 'БАЛАНС', 'Запасы'
FROM master.chart_of_accounts ca
WHERE ca.account_code LIKE '10%'
AND NOT EXISTS (
    SELECT 1 FROM master.account_rsbu_mapping m 
    WHERE m.account_id = ca.id AND m.rsbu_code = 1210
);

-- 62 "Расчеты с покупателями" → 1230
INSERT INTO master.account_rsbu_mapping (account_id, rsbu_code, form, comment)
SELECT ca.id, 1230, 'БАЛАНС', 'Дебиторская задолженность'
FROM master.chart_of_accounts ca
WHERE ca.account_code LIKE '62%'
AND NOT EXISTS (
    SELECT 1 FROM master.account_rsbu_mapping m 
    WHERE m.account_id = ca.id AND m.rsbu_code = 1230
);

-- 50,51,52,55 "Денежные средства" → 1250
INSERT INTO master.account_rsbu_mapping (account_id, rsbu_code, form, comment)
SELECT ca.id, 1250, 'БАЛАНС', 'Денежные средства и эквиваленты'
FROM master.chart_of_accounts ca
WHERE ca.account_code ~ '^(50|51|52|55)'
AND NOT EXISTS (
    SELECT 1 FROM master.account_rsbu_mapping m 
    WHERE m.account_id = ca.id AND m.rsbu_code = 1250
);

-- БАЛАНС: Пассив

-- 80 "Уставный капитал" → 1310
INSERT INTO master.account_rsbu_mapping (account_id, rsbu_code, form, comment)
SELECT ca.id, 1310, 'БАЛАНС', 'Уставный капитал'
FROM master.chart_of_accounts ca
WHERE ca.account_code LIKE '80%'
AND NOT EXISTS (
    SELECT 1 FROM master.account_rsbu_mapping m 
    WHERE m.account_id = ca.id AND m.rsbu_code = 1310
);

-- 84 "Нераспределенная прибыль" → 1370
INSERT INTO master.account_rsbu_mapping (account_id, rsbu_code, form, comment)
SELECT ca.id, 1370, 'БАЛАНС', 'Нераспределенная прибыль (непокрытый убыток)'
FROM master.chart_of_accounts ca
WHERE ca.account_code LIKE '84%'
AND NOT EXISTS (
    SELECT 1 FROM master.account_rsbu_mapping m 
    WHERE m.account_id = ca.id AND m.rsbu_code = 1370
);

-- 67 "Долгосрочные кредиты" → 1410
INSERT INTO master.account_rsbu_mapping (account_id, rsbu_code, form, comment)
SELECT ca.id, 1410, 'БАЛАНС', 'Заемные средства долгосрочные'
FROM master.chart_of_accounts ca
WHERE ca.account_code LIKE '67%'
AND NOT EXISTS (
    SELECT 1 FROM master.account_rsbu_mapping m 
    WHERE m.account_id = ca.id AND m.rsbu_code = 1410
);

-- 66 "Краткосрочные кредиты" → 1510
INSERT INTO master.account_rsbu_mapping (account_id, rsbu_code, form, comment)
SELECT ca.id, 1510, 'БАЛАНС', 'Заемные средства краткосрочные'
FROM master.chart_of_accounts ca
WHERE ca.account_code LIKE '66%'
AND NOT EXISTS (
    SELECT 1 FROM master.account_rsbu_mapping m 
    WHERE m.account_id = ca.id AND m.rsbu_code = 1510
);

-- 60 "Расчеты с поставщиками" → 1520
INSERT INTO master.account_rsbu_mapping (account_id, rsbu_code, form, comment)
SELECT ca.id, 1520, 'БАЛАНС', 'Кредиторская задолженность'
FROM master.chart_of_accounts ca
WHERE ca.account_code LIKE '60%'
AND NOT EXISTS (
    SELECT 1 FROM master.account_rsbu_mapping m 
    WHERE m.account_id = ca.id AND m.rsbu_code = 1520
);

-- ОФР: Доходы и расходы

-- 90.1 "Выручка" → 2110
INSERT INTO master.account_rsbu_mapping (account_id, rsbu_code, form, direction, comment)
SELECT ca.id, 2110, 'ОФР', 'CREDIT', 'Выручка от реализации'
FROM master.chart_of_accounts ca
WHERE ca.account_code LIKE '90.1%'
AND NOT EXISTS (
    SELECT 1 FROM master.account_rsbu_mapping m 
    WHERE m.account_id = ca.id AND m.rsbu_code = 2110
);

-- 90.2 "Себестоимость" → 2120
INSERT INTO master.account_rsbu_mapping (account_id, rsbu_code, form, direction, comment)
SELECT ca.id, 2120, 'ОФР', 'DEBIT', 'Себестоимость продаж'
FROM master.chart_of_accounts ca
WHERE ca.account_code LIKE '90.2%'
AND NOT EXISTS (
    SELECT 1 FROM master.account_rsbu_mapping m 
    WHERE m.account_id = ca.id AND m.rsbu_code = 2120
);

-- 91.1 "Прочие доходы" → 2340
INSERT INTO master.account_rsbu_mapping (account_id, rsbu_code, form, direction, comment)
SELECT ca.id, 2340, 'ОФР', 'CREDIT', 'Прочие доходы'
FROM master.chart_of_accounts ca
WHERE ca.account_code LIKE '91.1%'
AND NOT EXISTS (
    SELECT 1 FROM master.account_rsbu_mapping m 
    WHERE m.account_id = ca.id AND m.rsbu_code = 2340
);

-- 91.2 "Прочие расходы" → 2350
INSERT INTO master.account_rsbu_mapping (account_id, rsbu_code, form, direction, comment)
SELECT ca.id, 2350, 'ОФР', 'DEBIT', 'Прочие расходы'
FROM master.chart_of_accounts ca
WHERE ca.account_code LIKE '91.2%'
AND NOT EXISTS (
    SELECT 1 FROM master.account_rsbu_mapping m 
    WHERE m.account_id = ca.id AND m.rsbu_code = 2350
);

-- Статистика после загрузки базового маппинга
DO $$
DECLARE
    mapping_count INTEGER;
    accounts_mapped INTEGER;
    rsbu_mapped INTEGER;
BEGIN
    SELECT COUNT(*) INTO mapping_count FROM master.account_rsbu_mapping;
    SELECT COUNT(DISTINCT account_id) INTO accounts_mapped FROM master.account_rsbu_mapping;
    SELECT COUNT(DISTINCT rsbu_code) INTO rsbu_mapped FROM master.account_rsbu_mapping;
    
    RAISE NOTICE '✅ Базовый маппинг создан:';
    RAISE NOTICE '   • Связей: %', mapping_count;
    RAISE NOTICE '   • Счетов замаплено: %', accounts_mapped;
    RAISE NOTICE '   • Строк РСБУ замаплено: %', rsbu_mapped;
END $$;
