import pandas as pd
from finance_core.db.connector import DBManager

class AccountsLoader:
    def __init__(self):
        self.db_manager = DBManager()
        self.db = self.db_manager.get_arango_db()
        
        # Стандартный маппинг счетов РСБУ на строки баланса, группы ликвидности и Управленческие категории
        self.DEFAULT_MAPPING = {
            # === СЛОЖНЫЕ СЧЕТА (Развернутое сальдо) ===
            # 60: Расчеты с поставщиками
            '60.01': {'line': '1520', 'section': 'Краткосрочные обязательства', 'liquidity': 'P1', 'managerial': 'TradePayables'}, # Долг поставщику (Пассив)
            '60.02': {'line': '1230', 'section': 'Оборотные активы', 'liquidity': 'A2', 'managerial': 'Receivables'}, # Аванс выданный (Актив)
            '60.03': {'line': '1520', 'section': 'Краткосрочные обязательства', 'liquidity': 'P1', 'managerial': 'TradePayables'}, # Векселя

            # 62: Расчеты с покупателями
            '62.01': {'line': '1230', 'section': 'Оборотные активы', 'liquidity': 'A2', 'managerial': 'Receivables'}, # Долг покупателя (Актив)
            '62.02': {'line': '1520', 'section': 'Краткосрочные обязательства', 'liquidity': 'P1', 'managerial': 'AdvancesReceived'}, # Аванс полученный (Пассив)
            '62.03': {'line': '1520', 'section': 'Краткосрочные обязательства', 'liquidity': 'P1', 'managerial': 'AdvancesReceived'}, # Векселя

            # 76: Разные дебиторы и кредиторы (по умолчанию, уточняется по Виду)
            '76.АВ': {'line': '1220', 'section': 'Оборотные активы', 'liquidity': 'A3', 'managerial': 'Inventory'}, # НДС с авансов (Актив)
            '76.ВА': {'line': '1520', 'section': 'Краткосрочные обязательства', 'liquidity': 'P2', 'managerial': 'OtherPayables'}, # НДС с авансов (Пассив)

            # === АКТИВЫ (Uses of Funds / Production) ===
            
            # A1: Деньги -> Уменьшают Чистый Долг (Net Debt)
            '50': {'line': '1250', 'section': 'Оборотные активы', 'liquidity': 'A1', 'managerial': 'Cash'},
            '51': {'line': '1250', 'section': 'Оборотные активы', 'liquidity': 'A1', 'managerial': 'Cash'},
            '52': {'line': '1250', 'section': 'Оборотные активы', 'liquidity': 'A1', 'managerial': 'Cash'},
            '55': {'line': '1250', 'section': 'Оборотные активы', 'liquidity': 'A1', 'managerial': 'Cash'},
            '57': {'line': '1250', 'section': 'Оборотные активы', 'liquidity': 'A1', 'managerial': 'Cash'},
            '58': {'line': '1240', 'section': 'Оборотные активы', 'liquidity': 'A1', 'managerial': 'Cash'}, # Фин. вложения как кэш

            # A2: Дебиторка -> Часть Оборотного Капитала (Working Capital)
            '62': {'line': '1230', 'section': 'Оборотные активы', 'liquidity': 'A2', 'managerial': 'Receivables'},
            '71': {'line': '1230', 'section': 'Оборотные активы', 'liquidity': 'A2', 'managerial': 'Receivables'},
            '73': {'line': '1230', 'section': 'Оборотные активы', 'liquidity': 'A2', 'managerial': 'Receivables'},
            '75': {'line': '1230', 'section': 'Оборотные активы', 'liquidity': 'A2', 'managerial': 'Receivables'},
            '76': {'line': '1230', 'section': 'Оборотные активы', 'liquidity': 'A2', 'managerial': 'Receivables'},

            # A3: Запасы -> Часть Оборотного Капитала (Working Capital)
            '10': {'line': '1210', 'section': 'Оборотные активы', 'liquidity': 'A3', 'managerial': 'Inventory'},
            '19': {'line': '1220', 'section': 'Оборотные активы', 'liquidity': 'A3', 'managerial': 'Inventory'}, # НДС как оборотный актив
            '20': {'line': '1210', 'section': 'Оборотные активы', 'liquidity': 'A3', 'managerial': 'Inventory'},
            '21': {'line': '1210', 'section': 'Оборотные активы', 'liquidity': 'A3', 'managerial': 'Inventory'},
            '41': {'line': '1210', 'section': 'Оборотные активы', 'liquidity': 'A3', 'managerial': 'Inventory'},
            '43': {'line': '1210', 'section': 'Оборотные активы', 'liquidity': 'A3', 'managerial': 'Inventory'},
            '44': {'line': '1210', 'section': 'Оборотные активы', 'liquidity': 'A3', 'managerial': 'Inventory'},
            '45': {'line': '1210', 'section': 'Оборотные активы', 'liquidity': 'A3', 'managerial': 'Inventory'},
            '97': {'line': '1260', 'section': 'Оборотные активы', 'liquidity': 'A3', 'managerial': 'Inventory'},

            # A4: Внеоборотные -> Прочий Капитал / Основные средства (Fixed Assets)
            '01': {'line': '1150', 'section': 'Внеоборотные активы', 'liquidity': 'A4', 'managerial': 'FixedAssets'},
            '03': {'line': '1160', 'section': 'Внеоборотные активы', 'liquidity': 'A4', 'managerial': 'FixedAssets'},
            '04': {'line': '1110', 'section': 'Внеоборотные активы', 'liquidity': 'A4', 'managerial': 'FixedAssets'},
            '07': {'line': '1190', 'section': 'Внеоборотные активы', 'liquidity': 'A4', 'managerial': 'FixedAssets'},
            '08': {'line': '1190', 'section': 'Внеоборотные активы', 'liquidity': 'A4', 'managerial': 'FixedAssets'},
            '09': {'line': '1180', 'section': 'Внеоборотные активы', 'liquidity': 'A4', 'managerial': 'FixedAssets'},

            # === ПАССИВЫ (Sources of Funds / Funding) ===
            
            # П1: Кредиторская задолженность (Trade Payables) -> TO (Trade Obligations)
            '60': {'line': '1520', 'section': 'Краткосрочные обязательства', 'liquidity': 'P1', 'managerial': 'TradePayables'},

            # П1: Краткосрочные обязательства (Short-term Debt) -> Net Debt
            '66': {'line': '1510', 'section': 'Краткосрочные обязательства', 'liquidity': 'P1', 'managerial': 'ShortTermDebt'}, 

            # П2: Прочие обязательства (Other Payables) -> TO (Trade Obligations)
            '68': {'line': '1520', 'section': 'Краткосрочные обязательства', 'liquidity': 'P2', 'managerial': 'OtherPayables'}, # Налоги
            '69': {'line': '1520', 'section': 'Краткосрочные обязательства', 'liquidity': 'P2', 'managerial': 'OtherPayables'}, # Соцстрах
            '70': {'line': '1520', 'section': 'Краткосрочные обязательства', 'liquidity': 'P2', 'managerial': 'OtherPayables'}, # Зарплата
            '76': {'line': '1520', 'section': 'Краткосрочные обязательства', 'liquidity': 'P2', 'managerial': 'OtherPayables'}, # Прочие кредиторы
            '96': {'line': '1540', 'section': 'Краткосрочные обязательства', 'liquidity': 'P2', 'managerial': 'OtherPayables'},
            '98': {'line': '1530', 'section': 'Краткосрочные обязательства', 'liquidity': 'P2', 'managerial': 'OtherPayables'},

            # П3: Долгосрочные обязательства (Long-term Debt) -> Net Debt
            '67': {'line': '1410', 'section': 'Долгосрочные обязательства', 'liquidity': 'P3', 'managerial': 'LongTermDebt'},
            '77': {'line': '1420', 'section': 'Долгосрочные обязательства', 'liquidity': 'P3', 'managerial': 'LongTermDebt'},

            # П4: Собственный капитал -> Equity
            '80': {'line': '1310', 'section': 'Капитал и резервы', 'liquidity': 'P4', 'managerial': 'Equity'},
            '82': {'line': '1360', 'section': 'Капитал и резервы', 'liquidity': 'P4', 'managerial': 'Equity'},
            '83': {'line': '1350', 'section': 'Капитал и резервы', 'liquidity': 'P4', 'managerial': 'Equity'},
            '84': {'line': '1370', 'section': 'Капитал и резервы', 'liquidity': 'P4', 'managerial': 'Equity'},
            '86': {'line': '1300', 'section': 'Капитал и резервы', 'liquidity': 'P4', 'managerial': 'Equity'},
            '99': {'line': '1370', 'section': 'Капитал и резервы', 'liquidity': 'P4', 'managerial': 'Equity'},
        }

    def _sanitize_key(self, key: str) -> str:
        """Очищает ключ от недопустимых символов для ArangoDB"""
        # Разрешены: цифры, буквы, _, -, :, ., @, (, ), +, =, ,, ;, $, !, *, ', %
        # Но для счетов лучше оставить только цифры и точки
        import re
        return re.sub(r'[^0-9.]', '', key)

    def load_from_excel(self, file_path: str):
        """Загружает план счетов из Excel в ArangoDB"""
        print(f"📂 Чтение файла: {file_path}")
        df = pd.read_excel(file_path, dtype=str)
        
        # Нормализация имен колонок
        df.columns = [c.strip() for c in df.columns]
        
        accounts_coll = self.db.collection('Accounts')
        accounts_coll.truncate() # Очищаем перед загрузкой
        
        batch = []
        for _, row in df.iterrows():
            raw_code = str(row['Код счета']).strip()
            code = self._sanitize_key(raw_code)
            
            if not code:
                print(f"⚠️ Пропуск строки с некорректным кодом: {raw_code}")
                continue

            name = str(row['Наименование счета']).strip()
            kind_raw = str(row['Вид']).strip()
            
            # Определяем тип
            account_type = 'Active-Passive'
            if kind_raw == 'А': account_type = 'Active'
            elif kind_raw == 'П': account_type = 'Passive'
            
            # Пытаемся найти маппинг по коду счета (сначала точное совпадение, потом по группе)
            mapping = self._find_mapping(code)
            
            # Умная логика для активно-пассивных счетов (если маппинг не дал точного результата или это группа 76)
            if (not mapping.get('liquidity') or code.startswith('76')):
                if account_type == 'Active':
                    # Если счет Активный -> это Дебиторка (A2)
                    mapping['liquidity'] = 'A2'
                    mapping['managerial'] = 'Receivables'
                    mapping['section'] = 'Оборотные активы'
                    mapping['line'] = '1230'
                elif account_type == 'Passive':
                    # Если счет Пассивный -> это Кредиторка (P2)
                    mapping['liquidity'] = 'P2'
                    mapping['managerial'] = 'OtherPayables'
                    mapping['section'] = 'Краткосрочные обязательства'
                    mapping['line'] = '1520'

            doc = {
                '_key': code,
                'name': name,
                'type': account_type,
                'balance_line': mapping.get('line'),
                'balance_section': mapping.get('section'),
                'liquidity_group': mapping.get('liquidity'),
                'managerial_group': mapping.get('managerial'),
                'subconto': [
                    row.get('Субконто 1'),
                    row.get('Субконто 2'),
                    row.get('Субконто 3')
                ]
            }
            # Удаляем пустые субконто
            doc['subconto'] = [s for s in doc['subconto'] if pd.notna(s) and s != 'nan']
            
            batch.append(doc)
            
            if len(batch) >= 1000:
                accounts_coll.import_bulk(batch, on_duplicate='replace')
                batch = []
        
        if batch:
            accounts_coll.import_bulk(batch, on_duplicate='replace')
            
        print(f"✅ Загружено {accounts_coll.count()} счетов.")

    def _find_mapping(self, code: str):
        """Ищет маппинг для счета, проверяя группы (например, для 51.01 ищет 51)"""
        # 1. Точное совпадение
        if code in self.DEFAULT_MAPPING:
            return self.DEFAULT_MAPPING[code]
        
        # 2. Поиск по группе (первые 2 цифры)
        if len(code) >= 2:
            group = code[:2]
            if group in self.DEFAULT_MAPPING:
                return self.DEFAULT_MAPPING[group]
                
        return {'line': None, 'section': None, 'liquidity': None, 'managerial': None}

if __name__ == "__main__":
    loader = AccountsLoader()
    loader.load_from_excel('/opt/docagent/docs/a-findocs/План счетов.xlsx')
