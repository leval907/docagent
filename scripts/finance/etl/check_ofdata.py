#!/usr/bin/env python3
"""
Скрипт для проверки контрагентов через API ofdata.ru
"""

import sys
import json
import requests

API_KEY = "AoAiMP8MlVLeqSjK"
BASE_URL = "https://api.ofdata.ru/v2"

def get_company_info(inn):
    print(f"🔍 [OfData] Поиск компании по ИНН: {inn}")
    url = f"{BASE_URL}/company"
    params = {
        "key": API_KEY,
        "inn": inn
    }
    
    try:
        response = requests.get(url, params=params, timeout=10)
        if response.status_code == 200:
            data = response.json()
            print(json.dumps(data, ensure_ascii=False, indent=2))
            return data
        elif response.status_code == 404:
            print("❌ Компания не найдена")
        else:
            print(f"⚠ Ошибка API: {response.status_code}")
            print(response.text)
    except Exception as e:
        print(f"❌ Ошибка запроса: {e}")

def get_person_info(inn):
    print(f"🔍 [OfData] Поиск физлица по ИНН: {inn}")
    # Пробуем endpoint /person (физлица) и /entrepreneur (ИП)
    
    # 1. Entrepreneur (ИП)
    print("   Проверка в реестре ИП...")
    url_ip = f"{BASE_URL}/entrepreneur"
    params = {
        "key": API_KEY,
        "inn": inn
    }
    try:
        response = requests.get(url_ip, params=params, timeout=10)
        if response.status_code == 200:
            print("✅ Найдено в реестре ИП:")
            print(json.dumps(response.json(), ensure_ascii=False, indent=2))
        elif response.status_code != 404:
             print(f"⚠ Ошибка API (ИП): {response.status_code}")
    except Exception as e:
        print(f"❌ Ошибка запроса (ИП): {e}")

    # 2. Person (Физлицо - связи)
    print("   Проверка связей физлица...")
    url_person = f"{BASE_URL}/person"
    try:
        response = requests.get(url_person, params=params, timeout=10)
        if response.status_code == 200:
            print("✅ Найдены связи физлица:")
            print(json.dumps(response.json(), ensure_ascii=False, indent=2))
        elif response.status_code != 404:
             print(f"⚠ Ошибка API (Физлицо): {response.status_code}")
    except Exception as e:
        print(f"❌ Ошибка запроса (Физлицо): {e}")

def search_by_name(query):
    print(f"🔍 [OfData] Поиск по названию: {query}")
    url = f"{BASE_URL}/search"
    params = {
        "key": API_KEY,
        "query": query
    }
    try:
        response = requests.get(url, params=params, timeout=10)
        if response.status_code == 200:
            print(json.dumps(response.json(), ensure_ascii=False, indent=2))
        else:
            print(f"⚠ Ошибка API: {response.status_code}")
            print(response.text)
    except Exception as e:
        print(f"❌ Ошибка запроса: {e}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 check_ofdata.py <INN or Name>")
        sys.exit(1)
        
    query = sys.argv[1]
    if query.isdigit() and len(query) in [10, 12]:
        if len(query) == 10:
            get_company_info(query)
        else:
            get_person_info(query)
    else:
        search_by_name(query)
