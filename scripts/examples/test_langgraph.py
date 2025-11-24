import operator
import os
from typing import Annotated, TypedDict, Union

from dotenv import load_dotenv
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langchain_community.chat_models import GigaChat
from langgraph.graph import StateGraph, END

# Загружаем переменные окружения
load_dotenv()

# Инициализация GigaChat
llm = GigaChat(
    credentials=os.getenv("GIGACHAT_CREDENTIALS"),
    scope=os.getenv("GIGACHAT_SCOPE"),
    verify_ssl_certs=False
)

# 1. Определяем состояние (State)
class AgentState(TypedDict):
    messages: Annotated[list[BaseMessage], operator.add]

# 2. Определяем узлы (Nodes) - функции агента
def agent_node(state: AgentState):
    """Узел, который отправляет историю сообщений в GigaChat."""
    messages = state['messages']
    
    # Вызов LLM
    response = llm.invoke(messages)
    
    return {"messages": [response]}

def should_continue(state: AgentState):
    """Определяет, нужно ли продолжать выполнение."""
    messages = state['messages']
    last_message = messages[-1]
    
    if "стоп" in last_message.content.lower():
        return "end"
    return "continue"

# 3. Создаем граф
workflow = StateGraph(AgentState)

# Добавляем узлы
workflow.add_node("agent", agent_node)

# Устанавливаем точку входа
workflow.set_entry_point("agent")

# Добавляем условные переходы (если нужны) или просто завершаем
workflow.add_edge("agent", END)

# Компилируем граф
app = workflow.compile()

# 4. Функция для запуска из CLI
def run_cli():
    print("🤖 LangGraph Agent CLI (введите 'выход' для завершения)")
    print("-" * 50)
    
    while True:
        user_input = input("Вы: ")
        if user_input.lower() in ["выход", "exit", "quit"]:
            break
            
        inputs = {"messages": [HumanMessage(content=user_input)]}
        
        # Запуск графа
        for output in app.stream(inputs):
            for key, value in output.items():
                print(f"🤖 Агент ({key}): {value['messages'][-1].content}")
        print("-" * 50)

if __name__ == "__main__":
    run_cli()
