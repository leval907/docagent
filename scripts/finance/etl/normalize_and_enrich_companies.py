#!/usr/bin/env python3
"""
Нормализация и обогащение компаний:
1. Нормализует названия: "НАЗВАНИЕ ОПФ" (ПАРТНЕР ООО, АЛЬЯНС ООО)
2. Обогащает через DaData API
3. Находит и объединяет дубликаты по ИНН
"""

import sys
from pathlib import Path
import time
import re
from datetime import datetime
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


def normalize_company_name(name: str) -> str:
    """
    Нормализует название компании по правилам:
    - Убираем кавычки
    - Переставляем ОПФ в конец: ООО "ПАРТНЕР" -> ПАРТНЕР ООО
    - Для ИП: ИП Иванов -> Иванов Иван Иванович ИП
    - Физлица без изменений
    """
    if not name:
        return name
    
    # Убираем лишние пробелы и кавычки
    name = name.strip()
    name = name.replace('"', '').replace('"', '').replace('"', '')
    name = ' '.join(name.split())  # Множественные пробелы в один
    
    # Список ОПФ
    opf_list = [
        'ООО', 'ОАО', 'ЗАО', 'АО', 'ИП', 
        'ПАО', 'НАО', 'ГУП', 'МУП',
        'ТОО', 'ТДО', 'ОДО'
    ]
    
    # Паттерны для поиска ОПФ в начале/конце
    opf_start_pattern = r'^(' + '|'.join(opf_list) + r')\s+[""«]?(.+?)[""»]?$'
    opf_end_pattern = r'^[""«]?(.+?)[""»]?\s+(' + '|'.join(opf_list) + r')$'
    
    # Проверяем ОПФ в начале: ООО "ПАРТНЕР" -> ПАРТНЕР ООО
    match = re.match(opf_start_pattern, name, re.IGNORECASE)
    if match:
        opf = match.group(1).upper()
        company_name = match.group(2).strip()
        return f"{company_name} {opf}"
    
    # Проверяем ОПФ в конце: "ПАРТНЕР" ООО -> ПАРТНЕР ООО
    match = re.match(opf_end_pattern, name, re.IGNORECASE)
    if match:
        company_name = match.group(1).strip()
        opf = match.group(2).upper()
        return f"{company_name} {opf}"
    
    # Специальная обработка для ИП с ФИО
    if name.upper().startswith('ИП '):
        # ИП Иванов Иван Иванович -> Иванов Иван Иванович ИП
        fio = name[3:].strip()
        return f"{fio} ИП"
    
    # Если не нашли ОПФ - возвращаем как есть (возможно физлицо)
    return name


class CompanyNormalizer:
    def __init__(self):
        self.pg_conn = psycopg2.connect(**POSTGRES_CONFIG)
        self.stats = {
            'total': 0,
            'normalized': 0,
            'enriched': 0,
            'not_found': 0,
            'errors': 0,
            'duplicates_merged': 0
        }
    
    def __del__(self):
        if hasattr(self, 'pg_conn'):
            self.pg_conn.close()
    
    def normalize_all_names(self):
        """Нормализует все названия компаний"""
        print("\n" + "="*80)
        print("ЭТАП 1: Нормализация названий компаний")
        print("="*80)
        
        cursor = self.pg_conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute("SELECT id, company_name FROM master.companies ORDER BY id")
        companies = cursor.fetchall()
        
        for company in companies:
            old_name = company['company_name']
            new_name = normalize_company_name(old_name)
            
            if old_name != new_name:
                print(f"[{company['id']}] {old_name}")
                print(f"      → {new_name}")
                
                cursor.execute("""
                    UPDATE master.companies 
                    SET company_name = %s 
                    WHERE id = %s
                """, (new_name, company['id']))
                
                self.stats['normalized'] += 1
        
        self.pg_conn.commit()
        print(f"\n✅ Нормализовано: {self.stats['normalized']} компаний")
    
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
            return suggestions[0] if suggestions else None
            
        except Exception as e:
            print(f"⚠ Ошибка API: {e}")
            return None
    
    def extract_data(self, suggestion):
        """Извлекает данные из ответа DaData"""
        if not suggestion:
            return None
        
        data = suggestion.get("data", {})
        
        return {
            "inn": data.get("inn"),
            "ogrn": data.get("ogrn"),
            "full_name": data.get("name", {}).get("full_with_opf"),
            "short_name": data.get("name", {}).get("short_with_opf"),
            "address": data.get("address", {}).get("value"),
            "director_name": (data.get("management") or {}).get("name"),
            "phone": (data.get("phones", [None])[0] if data.get("phones") else None),
            "status": (data.get("state") or {}).get("status"),
            "registration_date": (data.get("state") or {}).get("registration_date"),
            "okved": data.get("okved")
        }
    
    def enrich_companies(self, limit=None):
        """Обогащает компании через DaData"""
        print("\n" + "="*80)
        print("ЭТАП 2: Обогащение через DaData API")
        print("="*80)
        
        cursor = self.pg_conn.cursor(cursor_factory=RealDictCursor)
        
        query = """
            SELECT id, company_name, inn 
            FROM master.companies 
            WHERE enrichment_status = 'pending' OR inn IS NULL
            ORDER BY id
        """
        if limit:
            query += f" LIMIT {limit}"
        
        cursor.execute(query)
        companies = cursor.fetchall()
        
        print(f"К обработке: {len(companies)} компаний\n")
        
        for idx, company in enumerate(companies, 1):
            print(f"[{idx}/{len(companies)}] {company['company_name']}")
            
            suggestion = self.dadata_suggest(company['company_name'])
            
            if suggestion:
                data = self.extract_data(suggestion)
                
                if data and data.get('inn'):
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
                            okved = %s,
                            enriched_at = NOW(),
                            enrichment_status = 'enriched'
                        WHERE id = %s
                    """, (
                        data['inn'], data['ogrn'], data['full_name'],
                        data['address'], data['director_name'], data['phone'],
                        data['status'], data['okved'], company['id']
                    ))
                    
                    print(f"  ✅ ИНН: {data['inn']}, {data['full_name']}")
                    self.stats['enriched'] += 1
                else:
                    cursor.execute("""
                        UPDATE master.companies 
                        SET enrichment_status = 'not_found', enriched_at = NOW()
                        WHERE id = %s
                    """, (company['id'],))
                    print(f"  ❌ Не найдено")
                    self.stats['not_found'] += 1
            else:
                cursor.execute("""
                    UPDATE master.companies 
                    SET enrichment_status = 'not_found', enriched_at = NOW()
                    WHERE id = %s
                """, (company['id'],))
                print(f"  ❌ Не найдено")
                self.stats['not_found'] += 1
            
            self.pg_conn.commit()
            time.sleep(0.3)  # Rate limit
        
        print(f"\n✅ Обогащено: {self.stats['enriched']}")
        print(f"❌ Не найдено: {self.stats['not_found']}")
    
    def find_and_merge_duplicates(self):
        """Находит дубликаты по ИНН и объединяет их"""
        print("\n" + "="*80)
        print("ЭТАП 3: Поиск и объединение дубликатов")
        print("="*80)
        
        cursor = self.pg_conn.cursor(cursor_factory=RealDictCursor)
        
        # Находим дубликаты по ИНН
        cursor.execute("""
            SELECT 
                inn,
                COUNT(*) as count,
                ARRAY_AGG(id ORDER BY id) as company_ids,
                ARRAY_AGG(company_name ORDER BY id) as names
            FROM master.companies
            WHERE inn IS NOT NULL AND inn != ''
            GROUP BY inn
            HAVING COUNT(*) > 1
            ORDER BY count DESC
        """)
        
        duplicates = cursor.fetchall()
        
        if not duplicates:
            print("✅ Дубликатов не найдено")
            return
        
        print(f"Найдено {len(duplicates)} групп дубликатов:\n")
        
        for dup in duplicates:
            print(f"ИНН: {dup['inn']}")
            print(f"  Компаний: {dup['count']}")
            for i, (cid, name) in enumerate(zip(dup['company_ids'], dup['names']), 1):
                print(f"  {i}. [{cid}] {name}")
            
            # Оставляем первую (с минимальным ID), остальные помечаем
            master_id = dup['company_ids'][0]
            duplicate_ids = dup['company_ids'][1:]
            
            print(f"  → Оставляем [{master_id}], помечаем остальные как дубликаты")
            
            # Обновляем ссылки в history.osv_detail
            for dup_id in duplicate_ids:
                cursor.execute("""
                    UPDATE history.osv_9m_summary 
                    SET company_id = %s 
                    WHERE company_id = %s
                """, (master_id, dup_id))
                
                cursor.execute("""
                    UPDATE history.cashflow_movements 
                    SET company_id = %s 
                    WHERE company_id = %s
                """, (master_id, dup_id))
                
                # Помечаем дубликат как неактивный
                cursor.execute("""
                    UPDATE master.companies 
                    SET 
                        is_active = FALSE,
                        enrichment_status = 'duplicate'
                    WHERE id = %s
                """, (dup_id,))
            
            self.stats['duplicates_merged'] += len(duplicate_ids)
            self.pg_conn.commit()
            print()
        
        print(f"✅ Объединено дубликатов: {self.stats['duplicates_merged']}")
    
    def run(self, enrich_limit=None):
        """Полный цикл обработки"""
        print("\n" + "="*80)
        print("🚀 НОРМАЛИЗАЦИЯ И ОБОГАЩЕНИЕ КОМПАНИЙ")
        print("="*80)
        
        cursor = self.pg_conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM master.companies")
        self.stats['total'] = cursor.fetchone()[0]
        print(f"Всего компаний: {self.stats['total']}")
        
        # Этап 1: Нормализация названий
        self.normalize_all_names()
        
        # Этап 2: Обогащение через DaData
        self.enrich_companies(limit=enrich_limit)
        
        # Этап 3: Объединение дубликатов
        self.find_and_merge_duplicates()
        
        # Итоговая статистика
        print("\n" + "="*80)
        print("✅ ОБРАБОТКА ЗАВЕРШЕНА")
        print("="*80)
        print(f"Всего компаний:        {self.stats['total']}")
        print(f"Нормализовано:         {self.stats['normalized']}")
        print(f"Обогащено:             {self.stats['enriched']}")
        print(f"Не найдено:            {self.stats['not_found']}")
        print(f"Объединено дубликатов: {self.stats['duplicates_merged']}")
        print("="*80)


def main():
    import argparse
    parser = argparse.ArgumentParser(description='Нормализация и обогащение компаний')
    parser.add_argument('--limit', type=int, help='Ограничить обогащение N компаний')
    parser.add_argument('--normalize-only', action='store_true', help='Только нормализация без API')
    
    args = parser.parse_args()
    
    normalizer = CompanyNormalizer()
    
    if args.normalize_only:
        normalizer.normalize_all_names()
    else:
        normalizer.run(enrich_limit=args.limit)


if __name__ == "__main__":
    main()
