import streamlit as st
import requests
import os

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")

st.set_page_config(page_title="Finance Dashboard", layout="wide")

st.title("📊 Финансовый анализ группы компаний")

st.sidebar.header("Навигация")
page = st.sidebar.radio("Выберите раздел", ["Обзор", "Консолидация", "Граф связей"])

if page == "Обзор":
    st.header("Статус системы")
    try:
        response = requests.get(f"{BACKEND_URL}/health")
        if response.status_code == 200:
            data = response.json()
            st.success("Backend доступен")
            st.json(data)
        else:
            st.error(f"Backend вернул ошибку: {response.status_code}")
    except Exception as e:
        st.error(f"Не удалось подключиться к Backend: {e}")

elif page == "Консолидация":
    st.header("Консолидированная выручка")
    st.info("Здесь будут таблицы из DuckDB")

elif page == "Граф связей":
    st.header("Граф транзакций")
    st.info("Здесь будет визуализация из ArangoDB")
