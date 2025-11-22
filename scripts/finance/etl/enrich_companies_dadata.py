#!/usr/bin/env python3
"""
Обогащение таблицы master.companies данными из DaData API
Получает: ИНН, ОГРН, полное наименование, адрес, руководителя, телефон, статус
"""

import sys
from pathlib import Path
import time
from datetime import datetime
import requests
import psycopg2
from psycopg2.extras import RealDictCursor

# Добавим путь к finance_core
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from finance_core.config import (
    POSTGRES_HOST, POSTGRES_PORT, POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_DB
)

# DaData API credentials
DADATA_API_KEY = "bd5917c0a335f0af9cceee3f0248b749898d3116"
DADATA_SECRET_KEY = "6eddd0943fc1170cfaa578c3337dbea97631d72f"
DADATA_SUGGEST_URL = "https://suggestions.dadata.ru/suggestions/api/4_1/rs/suggest/party"
DADATA_FINDBYID_URL = "https://suggestions.dadata.ru/suggestions/api/4_1/rs/findById/party"

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


class CompanyEnricher:
    def __init__(self):
        self.pg_conn = psycopg2.connect(**POSTGRES_CONFIG)
        self.stats = {
            'total': 0,
            'enriched': 0,
            'not_found': 0,
            'errors': 0
        }
    
    def __del__(self):
        if hasattr(self, 'pg_conn'):
            self.pg_conn.close()
    
    def dadata_suggest_company(self, name: str, max_results: int = 1):
        """
        Поиск компании по названию через /suggest/party
        """
        try:
            response = requests.post(
                DADATA_SUGGEST_URL,
                json={"query": name, "count": max_results},
                headers=HEADERS,
                timeout=10
            )
            
            if response.status_code != 200:
                print(f"⚠ DaData API error: {response.status_code} - {response.text}")
                return None
            
            result = response.json().get("suggestions", [])
            return result
        except Exception as e:
            print(f"❌ Exception in dadata_suggest_company: {e}")
            return None
    
    def dadata_findbyid(self, inn: str = None, ogrn: str = None):
        """
        Поиск компании по ИНН или ОГРН через /findById/party
        Возвращает полную информацию
        """
        if not inn and not ogrn:
            return None
        
        query = inn if inn else ogrn
        
        try:
            response = requests.post(
                DADATA_FINDBYID_URL,
                json={"query": query},
                headers=HEADERS,
                timeout=10
            )
            
            if response.status_code != 200:
                print(f"⚠ DaData API error: {response.status_code}")
                return None
            
            result = response.json().get("suggestions", [])
            return result[0] if result else None
        except Exception as e:
            print(f"❌ Exception in dadata_findbyid: {e}")
            return None
    
    def extract_company_data(self, suggestion):
        """
        Извлечение всех нужных полей из ответа DaData
        """
        if not suggestion:
            return None
        
        data = suggestion.get("data", {})
        
        # Извлекаем данные
        company_info = {
            "inn": data.get("inn"),
            "ogrn": data.get("ogrn"),
            "full_name": data.get("name", {}).get("full_with_opf"),
            "address": data.get("address", {}).get("value"),
            "director_name": None,
            "phone": None,
            "status": None,
            "registration_date": None,
            "liquidation_date": None,
            "okved": data.get("okved")
        }
        
        # Руководитель
        management = data.get("management")
        if management:
            company_info["director_name"] = management.get("name")
        
        # Телефон
        phones = data.get("phones")
        if phones and isinstance(phones, list) and len(phones) > 0:
            company_info["phone"] = phones[0]
        
        # Статус
        state = data.get("state")
        if state:
            company_info["status"] = state.get("status")
            
            # Даты
            reg_date = state.get("registration_date")
            if reg_date:
                # Формат: timestamp в миллисекундах или дата
                try:
                    if isinstance(reg_date, int):
                        company_info["registration_date"] = datetime.fromtimestamp(reg_date / 1000).date()
                    else:
                        company_info["registration_date"] = reg_date
                except:
                    pass
            
            liq_date = state.get("liquidation_date")
            if liq_date:
                try:
                    if isinstance(liq_date, int):
                        company_info["liquidation_date"] = datetime.fromtimestamp(liq_date / 1000).date()
                    else:
                        company_info["liquidation_date"] = liq_date
                except:
                    pass
        
        return company_info
    
    def update_company(self, company_id: int, company_data: dict, status: str = 'enriched'):
        """
        Обновление записи компании в БД
        """
        cursor = self.pg_conn.cursor()
        
        cursor.execute("""
            UPDATE master.companies
            SET 
                inn = %s,
                ogrn = %s,
                full_name = %s,
                address = %s,
                director_name = %s,
                phone = %s,
                status = %s,
                registration_date = %s,
                liquidation_date = %s,
                okved = %s,
                enriched_at = NOW(),
                enrichment_status = %s
            WHERE id = %s
        """, (
            company_data.get("inn"),
            company_data.get("ogrn"),
            company_data.get("full_name"),
            company_data.get("address"),
            company_data.get("director_name"),
            company_data.get("phone"),
            company_data.get("status"),
            company_data.get("registration_date"),
            company_data.get("liquidation_date"),
            company_data.get("okved"),
            status,
            company_id
        ))
        
        self.pg_conn.commit()
    
    def mark_not_found(self, company_id: int):
        """
        Пометить компанию как не найденную
        """
        cursor = self.pg_conn.cursor()
        cursor.execute("""
            UPDATE master.companies
            SET 
                enrichment_status = 'not_found',
                enriched_at = NOW()
            WHERE id = %s
        """, (company_id,))
        self.pg_conn.commit()
    
    def enrich_company(self, company_id: int, company_name: str, existing_inn: str = None):
        """
        Обогащение одной компании
        """
        print(f"\n{'='*80}")
        print(f"Обработка: [{company_id}] {company_name}")
        print(f"{'='*80}")
        
        # Если есть ИНН - используем findById для точности
        if existing_inn and len(existing_inn) >= 10:
            print(f"📋 Есть ИНН: {existing_inn}, используем findById...")
            suggestion = self.dadata_findbyid(inn=existing_inn)
            
            if suggestion:
                company_data = self.extract_company_data(suggestion)
                if company_data and company_data.get("inn"):
                    self.update_company(company_id, company_data, 'enriched')
                    print(f"✅ Обогащено через findById: {company_data.get('full_name')}")
                    print(f"   ИНН: {company_data.get('inn')}, ОГРН: {company_data.get('ogrn')}")
                    print(f"   Статус: {company_data.get('status')}")
                    self.stats['enriched'] += 1
                    return True
        
        # Иначе - поиск по названию
        print(f"🔍 Поиск по названию через suggest...")
        suggestions = self.dadata_suggest_company(company_name, max_results=3)
        
        if not suggestions:
            print(f"❌ Не найдено в DaData")
            self.mark_not_found(company_id)
            self.stats['not_found'] += 1
            return False
        
        # Берем первый (самый релевантный) результат
        best_match = suggestions[0]
        company_data = self.extract_company_data(best_match)
        
        if not company_data or not company_data.get("inn"):
            print(f"❌ Нет данных в ответе DaData")
            self.mark_not_found(company_id)
            self.stats['not_found'] += 1
            return False
        
        # Обновляем компанию
        self.update_company(company_id, company_data, 'enriched')
        
        print(f"✅ Обогащено: {company_data.get('full_name')}")
        print(f"   ИНН: {company_data.get('inn')}, ОГРН: {company_data.get('ogrn')}")
        print(f"   Адрес: {company_data.get('address')}")
        print(f"   Руководитель: {company_data.get('director_name')}")
        print(f"   Статус: {company_data.get('status')}")
        
        # Показываем альтернативы если есть
        if len(suggestions) > 1:
            print(f"\n   📌 Найдено еще {len(suggestions)-1} вариантов:")
            for i, alt in enumerate(suggestions[1:], 1):
                alt_data = alt.get("data", {})
                print(f"      {i}. {alt.get('value')} (ИНН: {alt_data.get('inn')})")
        
        self.stats['enriched'] += 1
        return True
    
    def run_enrichment(self, limit: int = None, only_empty: bool = True):
        """
        Массовое обогащение всех компаний
        """
        cursor = self.pg_conn.cursor(cursor_factory=RealDictCursor)
        
        # Формируем WHERE условие
        where_clause = ""
        if only_empty:
            where_clause = "WHERE (inn IS NULL OR inn = '' OR enrichment_status = 'pending')"
        
        # Получаем список компаний для обогащения
        query = f"""
            SELECT id, company_name, inn 
            FROM master.companies 
            {where_clause}
            ORDER BY id
        """
        
        if limit:
            query += f" LIMIT {limit}"
        
        cursor.execute(query)
        companies = cursor.fetchall()
        
        self.stats['total'] = len(companies)
        
        print("\n" + "="*80)
        print(f"🚀 НАЧАЛО ОБОГАЩЕНИЯ КОМПАНИЙ ЧЕРЕЗ DADATA")
        print("="*80)
        print(f"Всего компаний к обработке: {self.stats['total']}")
        print(f"API Key: {DADATA_API_KEY[:20]}...")
        print("="*80)
        
        if self.stats['total'] == 0:
            print("✅ Нет компаний для обогащения (все уже обработаны)")
            return
        
        # Обрабатываем компании
        for idx, company in enumerate(companies, 1):
            print(f"\n[{idx}/{self.stats['total']}]")
            
            try:
                self.enrich_company(
                    company['id'],
                    company['company_name'],
                    company.get('inn')
                )
                
                # Задержка между запросами (не превышаем лимиты DaData)
                time.sleep(0.3)
                
            except Exception as e:
                print(f"❌ Ошибка обработки: {e}")
                self.stats['errors'] += 1
                import traceback
                traceback.print_exc()
        
        # Итоги
        print("\n" + "="*80)
        print("✅ ОБОГАЩЕНИЕ ЗАВЕРШЕНО")
        print("="*80)
        print(f"Всего обработано:  {self.stats['total']}")
        print(f"✅ Обогащено:      {self.stats['enriched']}")
        print(f"❌ Не найдено:     {self.stats['not_found']}")
        print(f"⚠️  Ошибок:        {self.stats['errors']}")
        print("="*80)


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Обогащение компаний через DaData')
    parser.add_argument('--limit', type=int, help='Ограничить количество компаний')
    parser.add_argument('--all', action='store_true', help='Обработать все компании (включая уже обогащенные)')
    
    args = parser.parse_args()
    
    enricher = CompanyEnricher()
    enricher.run_enrichment(limit=args.limit, only_empty=not args.all)


if __name__ == "__main__":
    main()
