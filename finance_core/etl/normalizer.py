import pandas as pd
from pathlib import Path
import re
import warnings
from typing import List, Dict, Optional, Union

warnings.filterwarnings('ignore', category=UserWarning)

class OSVNormalizer:
    """
    Класс для нормализации оборотно-сальдовых ведомостей (ОСВ) из 1С.
    Приводит разрозненные Excel-файлы к единой структуре.
    """
    
    def __init__(self, group_companies_file: Optional[Path] = None):
        self.group_companies_file = group_companies_file
        self.group_companies = []
        if group_companies_file and group_companies_file.exists():
            self.load_group_companies()

    def load_group_companies(self) -> List[str]:
        """Загружает список компаний группы из Excel"""
        if not self.group_companies_file:
            return []
            
        try:
            df = pd.read_excel(self.group_companies_file)
            # Предполагаем, что колонка называется 'Группа компаний' или берем первую
            col_name = 'Группа компаний' if 'Группа компаний' in df.columns else df.columns[0]
            self.group_companies = df[col_name].dropna().astype(str).tolist()
            print(f"📋 Загружено {len(self.group_companies)} компаний группы")
            return self.group_companies
        except Exception as e:
            print(f"⚠️ Ошибка при загрузке списка компаний: {e}")
            return []

    def _looks_like_org(self, text: str) -> bool:
        """Проверяет, является ли текст названием организации"""
        if not isinstance(text, str):
            return False
        text_upper = text.upper()
        org_keywords = ['ООО', 'ОАО', 'ЗАО', 'ПАО', 'АО', 'ИП', 'ФГАУ', 'ФГУП', 'ФГБУ', 'МБУ', 'ГАУ', 'ГУП']
        return any(kw in text_upper for kw in org_keywords)

    def _looks_like_person_name(self, text: str) -> bool:
        """Проверяет, является ли текст ФИО физического лица"""
        if not isinstance(text, str) or len(text.strip()) < 5:
            return False
        text = text.strip()
        words = text.split()
        if not (2 <= len(words) <= 4):
            return False
        for word in words:
            if not (word[0].isupper() or word.isupper()):
                return False
        if self._looks_like_org(text):
            return False
        return True

    def normalize_file(self, file_path: Path, company_name: str) -> pd.DataFrame:
        """
        Нормализует один файл ОСВ.
        """
        print(f"📄 Обработка: {company_name} ({file_path.name})")
        
        try:
            # Читаем Excel с заголовками на строке 2
            df = pd.read_excel(file_path, header=2, engine='openpyxl')
        except Exception as e:
            print(f"❌ Ошибка чтения файла {file_path}: {e}")
            return pd.DataFrame()
        
        if len(df.columns) < 3:
            print(f"⚠️ Слишком мало колонок в файле {file_path}")
            return pd.DataFrame()

        # Первая колонка - Контрагент, вторая - Основание (документ)
        first_col = df.columns[0]
        second_col = df.columns[1]
        
        # Находим нужные колонки
        available_cols = {}
        
        for col in df.columns[2:]:
            col_str = str(col).strip()
            col_lower = col_str.lower()
            col_clean = col_lower.replace(' ', '')
            
            # Сальдо
            if 'начальное сальдо дт' in col_lower or col_str == 'Начальное сальдо Дт':
                available_cols['Начальное сальдо Дт'] = col
            elif 'начальное сальдо кт' in col_lower or col_str == 'Начальное сальдо Кт':
                available_cols['Начальное сальдо Кт'] = col
            elif 'конечное сальдо дт' in col_lower or col_str == 'Конечное сальдо Дт':
                available_cols['Конечное сальдо Дт'] = col
            elif 'конечное сальдо кт' in col_lower or col_str == 'Конечное сальдо Кт':
                available_cols['Конечное сальдо Кт'] = col
            
            # Обороты
            # 90 - выручка (Дт62 Кт90)
            elif (('дт62' in col_clean or 'д62' in col_clean) and ('кт90' in col_clean or 'к90' in col_clean)):
                available_cols['62_90'] = col
            # 91 - прочие доходы
            elif (('дт62' in col_clean or 'д62' in col_clean) and ('кт91' in col_clean or 'к91' in col_clean)):
                available_cols['62_91'] = col
            # 51 - оплата (Дт51 Кт62)
            elif (('дт51' in col_clean or 'д51' in col_clean) and ('кт62' in col_clean or 'к62' in col_clean)):
                available_cols['51_62'] = col
            # 62_51 - возврат (Дт62 Кт51)
            elif (('дт62' in col_clean or 'д62' in col_clean) and ('кт51' in col_clean or 'к51' in col_clean)):
                if '62_51' not in available_cols:
                    available_cols['62_51'] = col
            # 60 - взаимозачет (Дт60 Кт62)
            elif (('дт60' in col_clean or 'д60' in col_clean) and ('кт62' in col_clean or 'к62' in col_clean)):
                available_cols['60_62'] = col
            # 62_60 - обратный зачет
            elif (('дт62' in col_clean or 'д62' in col_clean) and ('кт60' in col_clean or 'к60' in col_clean)):
                if '62_60' not in available_cols:
                    available_cols['62_60'] = col
            # 76 - прочие расчеты (Дт76 Кт62)
            elif (('дт76' in col_clean or 'д76' in col_clean) and ('кт62' in col_clean or 'к62' in col_clean)):
                available_cols['76_62'] = col
            
            # Общие обороты
            elif col_lower == 'оборот дт' or col_str == 'Оборот Дт':
                available_cols['Оборот Дт'] = col
            elif col_lower == 'оборот кт' or col_str == 'Оборот Кт':
                available_cols['Оборот Кт'] = col

        normalized_rows = []
        
        for idx, row in df.iterrows():
            counterparty_cell = row[first_col]
            document_cell = row[second_col]
            
            if pd.isna(counterparty_cell):
                continue
            
            counterparty_str = str(counterparty_cell).strip()
            if not counterparty_str:
                continue
            
            if pd.isna(document_cell):
                document_str = "Сводная запись по контрагенту"
            else:
                document_str = str(document_cell).strip() or "Сводная запись по контрагенту"
            
            row_data = {
                'Компания': company_name,
                'Контрагент': counterparty_str,
                'Документ': document_str
            }
            
            for col_name, col_key in available_cols.items():
                value = row[col_key]
                if pd.notna(value):
                    try:
                        row_data[col_name] = float(value)
                    except:
                        row_data[col_name] = 0.0
                else:
                    row_data[col_name] = 0.0
            
            normalized_rows.append(row_data)
        
        result_df = pd.DataFrame(normalized_rows)
        print(f"   ✅ Нормализовано строк: {len(result_df)}")
        return result_df

    def _clean_company_name(self, file_name: str) -> str:
        """Извлекает чистое имя компании из названия файла"""
        # Убираем префиксы типа "исп_9.2025 "
        name = re.sub(r'^(исп\._|исп_|ипс_|и_)\d+\.\d{4}\s+', '', file_name)
        if name == file_name:
            name = re.sub(r'^(исп\.|ипс\.|и\.)', '', file_name)
            name = re.sub(r'_\d{6}$', '', name)
        return name.strip()

    def process_directory(self, input_dir: Path) -> pd.DataFrame:
        """Обрабатывает все Excel файлы в директории"""
        excel_files = sorted([
            f for f in input_dir.glob("*.xlsx") 
            if not f.name.startswith("~") and (not self.group_companies_file or f.name != self.group_companies_file.name)
        ])
        
        print(f"\n📂 Найдено файлов: {len(excel_files)}")
        all_data = []
        
        for file_path in excel_files:
            company_name = self._clean_company_name(file_path.stem)
            df = self.normalize_file(file_path, company_name)
            if not df.empty:
                all_data.append(df)
        
        if not all_data:
            return pd.DataFrame()
            
        combined_df = pd.concat(all_data, ignore_index=True)
        
        # Упорядочивание колонок
        ordered_cols = ['Компания', 'Контрагент', 'Документ']
        
        # Логический порядок: Сальдо -> Обороты -> Сальдо
        balance_start = ['Начальное сальдо Дт', 'Начальное сальдо Кт']
        turnovers = ['62_90', '62_91', '51_62', '60_62', '76_62', '62_51', '62_60', 'Оборот Дт', 'Оборот Кт']
        balance_end = ['Конечное сальдо Дт', 'Конечное сальдо Кт']
        
        final_cols = ordered_cols + \
                     [c for c in balance_start if c in combined_df.columns] + \
                     [c for c in turnovers if c in combined_df.columns] + \
                     [c for c in balance_end if c in combined_df.columns]
                     
        return combined_df[final_cols]
