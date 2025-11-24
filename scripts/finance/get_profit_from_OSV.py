import os
import logging
import datetime
import json
import re
from typing import Annotated, TypedDict, List, Dict, Any
import operator

from dotenv import load_dotenv
import psycopg2
from psycopg2.extras import RealDictCursor
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage
from langchain_community.chat_models import GigaChat
from langgraph.graph import StateGraph, END

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Database Configuration
DB_HOST = "localhost"
DB_NAME = "analytics"
DB_USER = "analytics_user"
DB_PASS = "analytics_secure_2025"

# GigaChat Configuration
llm = GigaChat(
    credentials=os.getenv("GIGACHAT_CREDENTIALS"),
    scope=os.getenv("GIGACHAT_SCOPE"),
    verify_ssl_certs=False,
    temperature=0.1 # Low temperature for more deterministic output
)

# --- Database Helper Functions ---

def get_db_connection():
    return psycopg2.connect(
        host=DB_HOST,
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASS
    )

def get_company_info(identifier: str):
    """Finds company info based on name, code, or ID."""
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    # Try to determine if identifier is an ID (int) or code/name (str)
    query = """
        SELECT id, company_code, company_name 
        FROM master.companies 
        WHERE company_code = %s OR company_name = %s
    """
    params = (identifier, identifier)
    
    if identifier.isdigit():
        query += " OR id = %s"
        params = (identifier, identifier, int(identifier))
        
    cur.execute(query, params)
    company = cur.fetchone()
    
    cur.close()
    conn.close()
    return company

def get_osv_data(company_id: int):
    """Fetches OSV data for the company."""
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    # Assuming history.osv_detail has company_id and account_code
    # We need to join with chart_of_accounts to get account names
    query = """
        SELECT 
            o.account_code,
            c.account_name,
            SUM(o.debit_turnover) as turnover_dt,
            SUM(o.credit_turnover) as turnover_kt
        FROM history.osv_detail o
        LEFT JOIN master.chart_of_accounts c ON o.account_code = c.account_code
        WHERE o.company_id = %s
        GROUP BY o.account_code, c.account_name
        ORDER BY o.account_code
    """
    cur.execute(query, (company_id,))
    data = cur.fetchall()
    
    cur.close()
    conn.close()
    return data

def find_value_for_column(column_name: str, data: Dict[str, Any]) -> float:
    """Helper to find value in data dict with fuzzy key matching."""
    # 1. Exact match
    if column_name in data:
        return data[column_name]
    
    # 2. Normalize strings for comparison
    def normalize(s):
        s = s.lower()
        # Replace common separators and variations
        s = s.replace("_", " ").replace("&", "and").replace("/", " ")
        # Remove non-alphanumeric (except spaces)
        s = "".join(c for c in s if c.isalnum() or c.isspace())
        # Collapse multiple spaces
        return " ".join(s.split())

    target_norm = normalize(column_name)
    
    for key, value in data.items():
        key_norm = normalize(key)
        
        # Check for match
        if key_norm == target_norm:
            return value
            
        # Handle specific variations like Amortisation (UK) vs Amortization (US)
        if "amortisation" in target_norm and "amortization" in key_norm:
             if key_norm.replace("amortization", "amortisation") == target_norm:
                 return value
                 
    return 0.0

def save_profit_report(company_code: str, company_name: str, report_data: Dict[str, Any]):
    """Saves the parsed report to analytics.profit_v."""
    conn = get_db_connection()
    cur = conn.cursor()
    
    # Delete existing record for this company to "replace" it
    cur.execute("DELETE FROM analytics.profit_v WHERE company_code = %s", (company_code,))
    
    insert_sql = """
        INSERT INTO analytics.profit_v (
            company_code, company_name, 
            "Revenue", "Cost of Goods", "Overheads", "Leasing",
            "Extraordinary Income/Expenses", "Interest Paid",
            "Depreciation & Amortisation", "Tax Paid", "Dividends Paid"
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """
    
    # Extract values using fuzzy matching
    values = (
        company_code,
        company_name,
        find_value_for_column("Revenue", report_data),
        find_value_for_column("Cost of Goods", report_data),
        find_value_for_column("Overheads", report_data),
        find_value_for_column("Leasing", report_data),
        find_value_for_column("Extraordinary Income/Expenses", report_data),
        find_value_for_column("Interest Paid", report_data),
        find_value_for_column("Depreciation & Amortisation", report_data),
        find_value_for_column("Tax Paid", report_data),
        find_value_for_column("Dividends Paid", report_data)
    )
    
    cur.execute(insert_sql, values)
    conn.commit()
    cur.close()
    conn.close()
    print(f"Data saved to analytics.profit_v for {company_name}")

def log_to_file(agent_name: str, company_name: str, response_text: str):
    """Logs the interaction to gigachat.log."""
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"""
[{timestamp}] Agent: {agent_name} | Company: {company_name}
Response:
{response_text}
--------------------------------------------------
"""
    with open("gigachat.log", "a", encoding="utf-8") as f:
        f.write(log_entry)

# --- LangGraph State & Nodes ---

class AgentState(TypedDict):
    company_identifier: str
    company_data: Dict[str, Any] # Stores company_code, name, id
    osv_data: List[Dict[str, Any]]
    llm_response: str
    parsed_json: Dict[str, Any]
    error: str

def fetch_data_node(state: AgentState):
    """Node to fetch company info and OSV data."""
    identifier = state['company_identifier']
    print(f"Searching for company: {identifier}")
    
    company = get_company_info(identifier)
    if not company:
        return {"error": f"Company not found: {identifier}"}
    
    print(f"Found company: {company['company_name']}")
    
    osv_rows = get_osv_data(company['id'])
    if not osv_rows:
        return {"error": f"No OSV data found for company: {company['company_name']}", "company_data": company}
        
    return {"company_data": company, "osv_data": osv_rows}

def generate_report_node(state: AgentState):
    """Node to call GigaChat."""
    if state.get('error'):
        return state
        
    company_name = state['company_data']['company_name']
    osv_data = state['osv_data']
    
    # Format OSV data for the prompt
    osv_text = "Account Code | Account Name | Turnover Dt | Turnover Kt\n"
    for row in osv_data:
        osv_text += f"{row['account_code']} | {row['account_name']} | {row['turnover_dt']} | {row['turnover_kt']}\n"
    
    prompt = f"""
    Ты - финансовый аналитик. Твоя задача - создать отчет о прибылях и убытках (P&L) на основе данных Оборотно-сальдовой ведомости (ОСВ).
    
    Вот данные ОСВ для компании "{company_name}":
    {osv_text}
    
    Проанализируй обороты по счетам (обычно 90, 91, 20, 26, 44 и другие счета учета затрат и выручки).
    Рассчитай следующие показатели и верни результат СТРОГО в формате JSON. Не пиши никакого вступительного текста, только JSON.
    
    Поля JSON должны быть (значения - числа с плавающей точкой):
    - "Revenue" (Выручка)
    - "Cost of Goods" (Себестоимость)
    - "Overheads" (Накладные расходы)
    - "Leasing" (Лизинг)
    - "Extraordinary Income/Expenses" (Прочие доходы/расходы)
    - "Interest Paid" (Проценты к уплате)
    - "Depreciation & Amortisation" (Амортизация)
    - "Tax Paid" (Налоги)
    - "Dividends Paid" (Дивиденды)
    - "message" (Строка с комментариями и пояснениями, если нужно пояснить расчеты)
    
    ВАЖНО:
    1. Не используй комментарии внутри JSON (// или #).
    2. Все арифметические действия (сложение, вычитание) выполни сам и запиши только итоговое число в основное поле.
    3. Если значение состоит из суммы нескольких чисел, добавь поле с суффиксом "_detail" (например, "Overheads_detail") и перечисли слагаемые в виде списка чисел.
    4. Если данных для показателя нет, ставь 0.0.
    
    Пример:
    {{
      "Overheads": 11679065.65,
      "Overheads_detail": [8722594.30, 2956471.35],
      "Revenue": 1000.0
    }}
    """
    
    print("Sending request to GigaChat...")
    response = llm.invoke([HumanMessage(content=prompt)])
    content = response.content
    
    print(f"Raw response from GigaChat:\n{content}")

    # Try to find JSON block using regex
    json_match = re.search(r'\{.*\}', content, re.DOTALL)
    if json_match:
        clean_content = json_match.group(0)
    else:
        clean_content = content.replace("```json", "").replace("```", "").strip()
    
    try:
        parsed = json.loads(clean_content)
    except json.JSONDecodeError:
        print("Failed to parse JSON from GigaChat response.")
        return {"llm_response": content, "error": "JSON Parsing Failed"}
        
    return {"llm_response": content, "parsed_json": parsed}

def save_result_node(state: AgentState):
    """Node to save results to DB and Log."""
    company = state.get('company_data', {})
    company_name = company.get('company_name', 'Unknown')

    if state.get('error'):
        error_msg = state['error']
        response = state.get('llm_response', 'No response')
        print(f"Error encountered: {error_msg}")
        
        log_text = f"ERROR: {error_msg}\nRaw Response:\n{response}"
        log_to_file("get_profit_from_OSV", company_name, log_text)
        return state
        
    response = state['llm_response']
    parsed = state['parsed_json']
    
    # 1. Log to file
    log_to_file("get_profit_from_OSV", company_name, response)
    
    # 2. Save to DB
    save_profit_report(company['company_code'], company['company_name'], parsed)
    
    return state

# --- Workflow Definition ---

workflow = StateGraph(AgentState)

workflow.add_node("fetch_data", fetch_data_node)
workflow.add_node("generate_report", generate_report_node)
workflow.add_node("save_result", save_result_node)

workflow.set_entry_point("fetch_data")

workflow.add_edge("fetch_data", "generate_report")
workflow.add_edge("generate_report", "save_result")
workflow.add_edge("save_result", END)

app = workflow.compile()

# --- CLI Entry Point ---

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python get_profit_from_OSV.py <company_identifier>")
        sys.exit(1)
        
    identifier = sys.argv[1]
    
    print(f"Starting agent for: {identifier}")
    inputs = {"company_identifier": identifier}
    
    for output in app.stream(inputs):
        pass # The nodes print their own status
        
    print("Agent finished.")
