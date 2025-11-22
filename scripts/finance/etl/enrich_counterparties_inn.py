#!/usr/bin/env python3
"""
Обогащение контрагентов только ИНН через DaData API
Быстрый режим для получения ключевого идентификатора
"""

import sys
from pathlib import Path
import time
import requests
import psycopg2
from psycopg2.extras import RealDictCursor

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from finance_core.config import (
    POSTGRES_HOST, POSTGRES_PORT, POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_DB
)

# DaData API
DADATA_API_KEY = "bd5917c0a335f0af9cceee3f0248b749898d3116"
DADATA_SUGGEST_URL = "https://suggestions.dadata.ru/suggestions/api/4_1/rs/suggest/party"

HEADERS = {
    "Authorization": f"Token {DADATA_API_KEY}",
    "Content-Type": "application/json",
    "Accept": "application/json"
}

POSTGRES_CONFIG = {
    'host': POSTGRES_HOST,
    'port': POSTGRES_PORT,
    'user': POSTGRES_USER,
    'password': POSTGRES_PASSWORD,
    'dbname': POSTGRES_DB
}


class CounterpartyINNEnricher:
    def __init__(self):
        self.pg_conn = psycopg2.connect(**POSTGRES_CONFIG)
        self.stats = {
            'total': 0,
            'enriched': 0,
            'not_found': 0,
            'already_have_inn': 0,
            'internal': 0,
            'errors': 0
        }
        # Загружаем список компаний группы для пометки внутренних контрагентов
        self.group_companies_inn = self._load_group_companies()
    
    def __del__(self):
        if hasattr(self, 'pg_conn'):
            self.pg_conn.close()
    
    def _load_group_companies(self):
        """Загрузка ИНН компаний группы"""
        cursor = self.pg_conn.cursor()
        cursor.execute("SELECT inn FROM master.companies WHERE inn IS NOT NULL AND inn != ''")
        return set(row[0] for row in cursor.fetchall())
    
    def dadata_suggest(self, name: str):
        """Поиск компании по названию"""
        try:
            response = requests.post(
                DADATA_SUGGEST_URL,
                json={"query": name, "count": 1},
                headers=HEADERS,
                timeout=10
            )
            
            if response.status_code != 200:
                return None
            
            suggestions = response.json().get("suggestions", [])
            if suggestions:
                data = suggestions[0].get("data", {})
                return {
                    "inn": data.get("inn"),
                    "full_name": data.get("name", {}).get("full_with_opf")
                }
            return None
            
        except Exception as e:
            print(f"⚠ Ошибка API: {e}")
            return None
    
    def enrich_counterparties(self, limit=None):
        """Обогащает контрагентов ИНН"""
        print("\n" + "="*80)
        print("🚀 ОБОГАЩЕНИЕ КОНТРАГЕНТОВ (ТОЛЬКО ИНН)")
        print("="*80)
        
        cursor = self.pg_conn.cursor(cursor_factory=RealDictCursor)
        
        # Выбираем контрагентов без ИНН
        query = """
            SELECT id, counterparty_name, inn, is_internal
            FROM master.counterparties 
            WHERE inn IS NULL OR inn = ''
            ORDER BY id
        """
        if limit:
            query += f" LIMIT {limit}"
        
        cursor.execute(query)
        counterparties = cursor.fetchall()
        
        self.stats['total'] = len(counterparties)
        
        print(f"К обработке: {self.stats['total']} контрагентов")
        print(f"Компаний группы (для пометки внутренних): {len(self.group_companies_inn)}")
        print()
        
        for idx, cp in enumerate(counterparties, 1):
            if idx % 50 == 0:
                print(f"\nОбработано {idx}/{self.stats['total']}...")
            
            # Если уже есть ИНН - пропускаем
            if cp['inn']:
                self.stats['already_have_inn'] += 1
                continue
            
            # Ищем в DaData
            result = self.dadata_suggest(cp['counterparty_name'])
            
            if result and result.get('inn'):
                inn = result['inn']
                
                # Проверяем, внутренняя ли компания
                is_internal = inn in self.group_companies_inn
                
                # Обновляем
                cursor.execute("""
                    UPDATE master.counterparties
                    SET 
                        inn = %s,
                        is_internal = %s
                    WHERE id = %s
                """, (inn, is_internal, cp['id']))
                
                status = "ВНУТРЕННЯЯ" if is_internal else "внешняя"
                print(f"[{idx}] ✅ {cp['counterparty_name'][:40]:40} → ИНН: {inn} ({status})")
                
                if is_internal:
                    self.stats['internal'] += 1
                else:
                    self.stats['enriched'] += 1
                
                self.pg_conn.commit()
            else:
                print(f"[{idx}] ❌ {cp['counterparty_name'][:40]:40} → не найдено")
                self.stats['not_found'] += 1
            
            time.sleep(0.3)  # Rate limit
        
        print("\n" + "="*80)
        print("✅ ОБОГАЩЕНИЕ ЗАВЕРШЕНО")
        print("="*80)
        print(f"Всего обработано:     {self.stats['total']}")
        print(f"✅ Обогащено ИНН:     {self.stats['enriched']}")
        print(f"🏢 Внутренние:        {self.stats['internal']}")
        print(f"❌ Не найдено:        {self.stats['not_found']}")
        print(f"ℹ️  Уже были ИНН:     {self.stats['already_have_inn']}")
        print("="*80)


def main():
    import argparse
    parser = argparse.ArgumentParser(description='Обогащение контрагентов ИНН')
    parser.add_argument('--limit', type=int, help='Ограничить количество')
    
    args = parser.parse_args()
    
    enricher = CounterpartyINNEnricher()
    enricher.enrich_counterparties(limit=args.limit)


if __name__ == "__main__":
    main()
