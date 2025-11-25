import requests
import json
import sys

def check_company(query):
    url = "https://suggestions.dadata.ru/suggestions/api/4_1/rs/suggest/party"
    token = "bd5917c0a335f0af9cceee3f0248b749898d3116"
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Authorization": f"Token {token}"
    }
    data = {
        "query": query,
        "count": 5
    }
    
    try:
        response = requests.post(url, json=data, headers=headers)
        response.raise_for_status()
        result = response.json()
        return result.get("suggestions", [])
    except Exception as e:
        print(f"Error querying Dadata: {e}")
        return []

def print_company_info(suggestion):
    data = suggestion['data']
    print(f"--- {suggestion['value']} ---")
    print(f"ИНН: {data.get('inn')} / КПП: {data.get('kpp')}")
    print(f"ОГРН: {data.get('ogrn')}")
    print(f"Адрес: {data.get('address', {}).get('value')}")
    print(f"Статус: {data.get('state', {}).get('status')} ({data.get('state', {}).get('actuality_date')})")
    
    mgmt = data.get('management')
    if mgmt:
        print(f"Руководитель: {mgmt.get('name')} ({mgmt.get('post')})")
    
    print(f"Тип: {data.get('type')}")
    if data.get('branch_type') == 'BRANCH':
        print("Это ФИЛИАЛ")
    
    # Finance (if available in free tier/suggestion)
    # Usually suggestions don't have deep finance, but let's see.
    
    print("-" * 30)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 check_company_dadata.py <INN or Name>")
        sys.exit(1)
    
    query = sys.argv[1]
    suggestions = check_company(query)
    
    if not suggestions:
        print("Ничего не найдено.")
    else:
        print(f"Найдено {len(suggestions)} вариантов:")
        for s in suggestions:
            print_company_info(s)
