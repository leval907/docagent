#!/usr/bin/env python3
"""
Скрипт для получения детальной информации о компании через DaData API по ИНН.
Ищет связи, учредителей, филиалы и другую информацию.
"""

import sys
import json
import requests
from datetime import datetime

# DaData API credentials (из найденного скрипта)
DADATA_API_KEY = "bd5917c0a335f0af9cceee3f0248b749898d3116"
DADATA_FINDBYID_URL = "https://suggestions.dadata.ru/suggestions/api/4_1/rs/findById/party"

HEADERS = {
    "Authorization": f"Token {DADATA_API_KEY}",
    "Content-Type": "application/json",
    "Accept": "application/json"
}

def get_company_info(inn):
    print(f"🔍 Поиск информации по ИНН: {inn}")
    
    try:
        response = requests.post(
            DADATA_FINDBYID_URL,
            json={"query": inn},
            headers=HEADERS,
            timeout=10
        )
        
        if response.status_code != 200:
            print(f"⚠ Ошибка API: {response.status_code}")
            print(response.text)
            return None
            
        data = response.json()
        suggestions = data.get("suggestions", [])
        
        if not suggestions:
            print("❌ Компания не найдена")
            return None
            
        company = suggestions[0]
        data = company.get("data", {})
        
        print(f"\n🏢 {company.get('value')}")
        print(f"   ИНН: {data.get('inn')} / КПП: {data.get('kpp')}")
        print(f"   ОГРН: {data.get('ogrn')}")
        print(f"   Адрес: {data.get('address', {}).get('value')}")
        print(f"   Статус: {data.get('state', {}).get('status')}")
        
        # Руководство
        mgmt = data.get('management')
        if mgmt:
            print(f"   Руководитель: {mgmt.get('name')} ({mgmt.get('post')})")
        else:
            print("   Руководитель: Н/Д (возможно, управляется УК)")

        # Учредители (если есть в ответе, обычно в платной версии, но проверим)
        founders = data.get('founders')
        if founders:
             print(f"   Учредители: {founders}")

        # Группа / Связи (если есть)
        group = data.get('group')
        if group:
             print(f"   Группа: {group}")

        # Managers (Управляющая компания часто здесь)
        managers = data.get('managers')
        if managers:
             print(f"   Управляющие: {managers}")

        print("\n📋 Полный JSON (для анализа):")
        print(json.dumps(company, ensure_ascii=False, indent=2))
        
        return company

    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return None

def get_company_suggestions(query):
    print(f"🔍 Поиск компании по названию: {query}")
    DADATA_SUGGEST_URL = "https://suggestions.dadata.ru/suggestions/api/4_1/rs/suggest/party"
    
    try:
        response = requests.post(
            DADATA_SUGGEST_URL,
            json={"query": query, "count": 5},
            headers=HEADERS,
            timeout=10
        )
        
        if response.status_code != 200:
            print(f"⚠ Ошибка API: {response.status_code}")
            return None
            
        suggestions = response.json().get("suggestions", [])
        
        if not suggestions:
            print("❌ Компании не найдены")
            return None
            
        print(f"✅ Найдено {len(suggestions)} вариантов:")
        for i, s in enumerate(suggestions, 1):
            data = s.get("data", {})
            print(f"\n{i}. {s.get('value')}")
            print(f"   ИНН: {data.get('inn')} / ОГРН: {data.get('ogrn')}")
            print(f"   Адрес: {data.get('address', {}).get('value')}")
            print(f"   Статус: {data.get('state', {}).get('status')}")
            print(f"   Руководитель: {data.get('management', {}).get('name') if data.get('management') else 'Н/Д'}")
            
        return suggestions

    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return None

if __name__ == "__main__":
    if len(sys.argv) > 1:
        query = sys.argv[1]
        # Если похоже на ИНН (цифры), ищем по ID, иначе suggest
        if query.isdigit() and len(query) in [10, 12]:
            get_company_info(query)
        else:
            get_company_suggestions(query)
    else:
        print("Использование: python3 check_company_dadata.py <ИНН или Название>")
