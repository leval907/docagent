#!/usr/bin/env python3
"""
Шаг 1: Нормализация оборотно-сальдовых ведомостей из 1С
Преобразует иерархическую структуру (Контрагент → Документы) в плоскую таблицу
"""

import pandas as pd
from pathlib import Path

# === Пути ===
FOLDER = Path("/opt/docagent/data/osv_revenue_0925/input")
OUTPUT_FOLDER = Path("/opt/docagent/data/osv_revenue_0925/output")
OUTPUT_FOLDER.mkdir(parents=True, exist_ok=True)

# --- Ключевые слова и функции ---
DOC_KEYWORDS = ["договор", "счет", "счёт", "акт", "дс", "доп.сог", "соглашение", "счет-фактура"]
ORG_TOKENS = ["ооо", "зао", "оао", "пао", "ао", "ано", "аноо", "ип", "нко", "гбу", "фонд", "ук", "упк"]


def is_doc_row(text: str) -> bool:
    """Проверяет, является ли строка документом"""
    t = str(text).lower()
    return any(k in t for k in DOC_KEYWORDS)


def looks_like_org(text: str) -> bool:
    """Проверяет, похожа ли строка на название организации"""
    t = str(text).lower()
    # Расширенный список организационных форм
    org_tokens_extended = ORG_TOKENS + ["фгау", "фгуп", "фгбу", "мбу", "гау", "гуп"]
    return any(f" {tok} " in f" {t} " or t.endswith(f" {tok}") for tok in org_tokens_extended)


def looks_like_person_name(text: str) -> bool:
    """Проверяет, похожа ли строка на ФИО (2-4 слова)"""
    words = str(text).strip().split()
    # ФИО обычно 2-4 слова
    if len(words) in [2, 3, 4]:
        # Проверяем, что первое слово — фамилия (начинается с заглавной)
        # и второе — имя (начинается с заглавной)
        if len(words) >= 2:
            first_word = words[0]
            second_word = words[1]
            # Все заглавные ИЛИ с заглавной буквы
            if (first_word[0].isupper() and second_word[0].isupper() and
                not any(x in text.lower() for x in ['договор', 'счет', 'акт'])):
                return True
    return False


def is_counterparty_row(text: str) -> bool:
    """Проверяет, является ли строка контрагентом (организация или ФИО)"""
    return looks_like_org(text) or looks_like_person_name(text)


def find_total_row(df: pd.DataFrame) -> dict:
    """
    Находит строку Итого и возвращает суммы для сверки с нормализованными данными
    """
    mask = df["Счет"].astype(str).str.lower().str.contains("итого|всего", na=False)
    if mask.any():
        total_row = df.loc[mask].iloc[-1]  # последняя строка с 'итого'
        
        def safe_numeric(value):
            """Безопасное преобразование в число"""
            result = pd.to_numeric(value, errors='coerce')
            return 0 if pd.isna(result) else float(result)
        
        total_values = {
            "Оборот Дт": safe_numeric(total_row.get("Оборот Дт", 0)),
            "Оборот Кт": safe_numeric(total_row.get("Оборот Кт", 0)),
            "90": safe_numeric(total_row.get("90", 0)),
            "91": safe_numeric(total_row.get("91", 0)),
            "51": safe_numeric(total_row.get("51", 0)),
            "62": safe_numeric(total_row.get("62", 0)),
        }
        return total_values
    return None


def normalize_1c_oborotka(df: pd.DataFrame) -> pd.DataFrame:
    """
    Преобразует иерархическую оборотку 1С в плоский вид.

    Структура файла 1С:
    - Контрагент (ООО/АО) - итоговая строка (пропускаем)
    - └─ Документ 1 - берем обороты
    - └─ Документ 2 - берем обороты
    - Следующий контрагент...

    Логика:
    1. Строка с ООО/АО/ЗАО = контрагент (запоминаем имя)
    2. Строки после контрагента БЕЗ ООО/АО = документы (берем данные)
    3. Встретили новое ООО/АО = новый контрагент
    """
    # Нормализуем названия колонок
    df = df.rename(columns=lambda x: str(x).strip())
    if "Счет" not in df.columns and "Счёт" in df.columns:
        df = df.rename(columns={"Счёт": "Счет"})
    if "Счет" not in df.columns:
        return pd.DataFrame()

        # Отфильтровываем пустые строки по "Счет"
    df = df[df["Счет"].notna()]
    df = df[~df["Счет"].astype(str).str.strip()
             .isin(["Счет", "Контрагенты", "Договоры", "62"])]
    
    # Убираем строку "Итого" в конце (но оставляем для сверки)
    mask_itogo = df["Счет"].astype(str).str.lower().str.contains("итого|всего", na=False)
    df_clean = df[~mask_itogo].copy()

    current_counterparty = None
    in_physical_persons_section = False
    rows = []

    for idx, row in df_clean.iterrows():
        text = str(row["Счет"]).strip()
        
        # Проверяем, это контрагент (организация или ФИО)?
        if is_counterparty_row(text):
            # Это итоговая строка контрагента - ТОЛЬКО запоминаем имя, НЕ добавляем в базу
            current_counterparty = text
            in_physical_persons_section = False  # Выходим из секции физлиц
            continue
        
        # Проверяем, это обобщенная строка "Физическое лицо" (итоговая)
        if ("физическое лицо" in text.lower() or "физ. лицо" in text.lower() or "физ.лицо" in text.lower()) and not text.startswith("ФЛ ("):
            # Это итоговая строка по физлицам - запоминаем как контрагента
            # Все следующие документы до нового контрагента будут под "Физическое лицо"
            current_counterparty = text
            in_physical_persons_section = True
            continue
        
        # Определяем контрагента для текущей строки
        if in_physical_persons_section:
            # В секции физлиц документы идут под контрагентом "Физическое лицо"
            # Для адресов "ФЛ (" - используем сам адрес как контрагента
            if text.startswith("ФЛ ("):
                counterparty_for_row = text
            elif is_doc_row(text):
                # Документ под "Физическое лицо"
                counterparty_for_row = current_counterparty
            else:
                # Неизвестная строка - пропускаем
                counterparty_for_row = None
        elif current_counterparty:
            counterparty_for_row = current_counterparty
        else:
            counterparty_for_row = None
        
        # Это документ под контрагентом - добавляем в базу
        if counterparty_for_row:
            # Берем числовые значения из строки документа
            nach_saldo_dt = pd.to_numeric(row.get("Начальное сальдо Дт", 0), errors="coerce")
            nach_saldo_kt = pd.to_numeric(row.get("Начальное сальдо Кт", 0), errors="coerce")
            oborot_dt = pd.to_numeric(row.get("Оборот Дт", 0), errors="coerce")
            oborot_kt = pd.to_numeric(row.get("Оборот Кт", 0), errors="coerce")
            s90 = pd.to_numeric(row.get("90", 0), errors="coerce")
            s91 = pd.to_numeric(row.get("91", 0), errors="coerce") if "91" in df.columns else 0
            s51 = pd.to_numeric(row.get("51", 0), errors="coerce")
            s62 = pd.to_numeric(row.get("62", 0), errors="coerce")
            s62_1 = pd.to_numeric(row.get("62.1", 0), errors="coerce") if "62.1" in df.columns else 0
            kon_saldo_dt = pd.to_numeric(row.get("Конечное сальдо Дт", 0), errors="coerce")
            kon_saldo_kt = pd.to_numeric(row.get("Конечное сальдо Кт", 0), errors="coerce")
            
            # Заменяем NaN на 0
            nach_saldo_dt = 0 if pd.isna(nach_saldo_dt) else nach_saldo_dt
            nach_saldo_kt = 0 if pd.isna(nach_saldo_kt) else nach_saldo_kt
            oborot_dt = 0 if pd.isna(oborot_dt) else oborot_dt
            oborot_kt = 0 if pd.isna(oborot_kt) else oborot_kt
            s90 = 0 if pd.isna(s90) else s90
            s91 = 0 if pd.isna(s91) else s91
            s51 = 0 if pd.isna(s51) else s51
            s62 = 0 if pd.isna(s62) else s62
            s62_1 = 0 if pd.isna(s62_1) else s62_1
            kon_saldo_dt = 0 if pd.isna(kon_saldo_dt) else kon_saldo_dt
            kon_saldo_kt = 0 if pd.isna(kon_saldo_kt) else kon_saldo_kt
            
            # Добавляем документ только если есть хоть какие-то обороты
            if oborot_dt != 0 or oborot_kt != 0 or s90 != 0 or s91 != 0 or s51 != 0 or s62 != 0:
                rows.append({
                    "Контрагент": counterparty_for_row,
                    "Документ": text,
                    "Начальное сальдо Дт": nach_saldo_dt,
                    "Начальное сальдо Кт": nach_saldo_kt,
                    "Оборот Дт": oborot_dt,
                    "Оборот Кт": oborot_kt,
                    "90": s90,
                    "91": s91,
                    "51": s51,
                    "62": s62,
                    "62.1": s62_1,
                    "Конечное сальдо Дт": kon_saldo_dt,
                    "Конечное сальдо Кт": kon_saldo_kt
                })

    return pd.DataFrame(rows)


def build_normalized_table(folder: Path) -> pd.DataFrame:
    """
    Формирование объединённой нормализованной таблицы из всех Excel-файлов
    """
    print("📊 Шаг 1: Нормализация данных из 1С (9 месяцев 2025)")
    print("=" * 80)

    all_data = []
    for file in sorted(folder.glob("9.2025 *.xlsx")):
        company = file.stem.replace("9.2025 ", "")
        print(f"📄 Обработка: {company}")

        # Читаем файл
        df_raw = pd.read_excel(file, header=5, engine="openpyxl")

        # Ищем строку "Итого" для контроля
        total_check = find_total_row(df_raw)

        # Нормализуем
        df_norm = normalize_1c_oborotka(df_raw)

        if df_norm.empty:
            print(f"  ⚠️  Нет данных после нормализации")
            continue

        df_norm["Компания"] = company
        all_data.append(df_norm)
        print(f"  ✅ Нормализовано: {len(df_norm)} документов")

        # Проверка суммы с "Итого" из 1С
        if total_check:
            sum_dt = df_norm["Оборот Дт"].sum()
            sum_kt = df_norm["Оборот Кт"].sum()
            sum_90 = df_norm["90"].sum()
            sum_91 = df_norm["91"].sum()
            sum_51 = df_norm["51"].sum()
            sum_62 = df_norm["62"].sum()

            diff_dt = abs(sum_dt - total_check["Оборот Дт"])
            diff_kt = abs(sum_kt - total_check["Оборот Кт"])
            diff_90 = abs(sum_90 - total_check["90"])
            diff_91 = abs(sum_91 - total_check["91"])
            diff_51 = abs(sum_51 - total_check["51"])
            diff_62 = abs(sum_62 - total_check["62"])

            # Допустимая погрешность 1 рубль
            if diff_dt < 1 and diff_kt < 1 and diff_90 < 1 and diff_91 < 1:
                print(f"  ✅ Проверка Итого: совпадает с 1С (Дт={sum_dt:,.2f}, Кт={sum_kt:,.2f})")
            else:
                print(f"  ⚠️  Расхождение с 1С:")
                if diff_dt >= 1:
                    print(f"     Оборот Дт: расхождение {diff_dt:,.2f} руб. (1С: {total_check['Оборот Дт']:,.2f}, факт: {sum_dt:,.2f})")
                if diff_kt >= 1:
                    print(f"     Оборот Кт: расхождение {diff_kt:,.2f} руб. (1С: {total_check['Оборот Кт']:,.2f}, факт: {sum_kt:,.2f})")
                if diff_90 >= 1:
                    print(f"     Счет 90: расхождение {diff_90:,.2f} руб. (1С: {total_check['90']:,.2f}, факт: {sum_90:,.2f})")
                if diff_91 >= 1:
                    print(f"     Счет 91: расхождение {diff_91:,.2f} руб. (1С: {total_check['91']:,.2f}, факт: {sum_91:,.2f})")
                if diff_51 >= 1:
                    print(f"     Счет 51: расхождение {diff_51:,.2f} руб. (1С: {total_check['51']:,.2f}, факт: {sum_51:,.2f})")
                if diff_62 >= 1:
                    print(f"     Счет 62: расхождение {diff_62:,.2f} руб. (1С: {total_check['62']:,.2f}, факт: {sum_62:,.2f})")
        else:
            print(f"  ⚠️  Строка 'Итого' не найдена в файле - сверка невозможна")

    if not all_data:
        raise RuntimeError("Не найдено данных для нормализации.")

    # Объединяем все данные
    combined = pd.concat(all_data, ignore_index=True)

    # Сохраняем промежуточный результат
    out_xlsx = OUTPUT_FOLDER / "normalized_osv.xlsx"
    combined.to_excel(out_xlsx, index=False, engine="openpyxl")

    print("=" * 80)
    print(f"💾 Нормализованная таблица сохранена: {out_xlsx}")
    print(f"📊 Всего документов: {len(combined)}")
    print(f"📋 Компаний: {combined['Компания'].nunique()}")
    print(f"👥 Уникальных контрагентов: {combined['Контрагент'].nunique()}")

    # Статистика по проводкам Д62 К90 (основная выручка) и Д62 К91 (прочие доходы)
    revenue_90 = combined[(combined['90'] > 0) & (combined['Оборот Дт'] > 0)]
    revenue_91 = combined[(combined['91'] > 0) & (combined['Оборот Дт'] > 0)]
    
    print(f"\n💰 Выручка за 9 месяцев 2025 года:")
    print(f"   Счет 90 (основная деятельность): {revenue_90['90'].sum():,.2f} руб.")
    print(f"   Счет 91 (прочие доходы): {revenue_91['91'].sum():,.2f} руб.")
    print(f"   " + "=" * 60)
    print(f"   ИТОГО выручка (90 + 91): {revenue_90['90'].sum() + revenue_91['91'].sum():,.2f} руб.")

    return combined


if __name__ == "__main__":
    try:
        df = build_normalized_table(FOLDER)
        print("\n✅ Нормализация завершена успешно!")
    except Exception as e:
        print(f"\n❌ Ошибка: {e}")
        raise
