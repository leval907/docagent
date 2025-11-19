#!/usr/bin/env python3
"""
Анализ по лотам с группировкой объектов и детализацией техники (ОС)
"""

import sys
from pathlib import Path
import pandas as pd

# Добавляем путь к модулям
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from scripts.analytics.duckdb_analytics import DuckDBAnalytics


def analyze_lots_structure():
    """Анализирует структуру лотов: объекты и техника"""
    
    db_path = "knowledge_base/duckdb/calculator/project1_calculator.duckdb"
    analytics = DuckDBAnalytics(db_path)
    
    print("\n" + "="*120)
    print("📊 СТРУКТУРА ЛОТОВ: ОБЪЕКТЫ И ОСНОВНЫЕ СРЕДСТВА (ТЕХНИКА)")
    print("="*120 + "\n")
    
    # Получаем уникальные лоты
    lots = analytics.query("""
        SELECT DISTINCT "Лот №"
        FROM cities_areas
        WHERE "Лот №" IS NOT NULL
        ORDER BY "Лот №"
    """)
    
    for lot_row in lots:
        lot_num = lot_row[0]
        
        print(f"\n{'='*120}")
        print(f"🏢 ЛОТ {lot_num}")
        print(f"{'='*120}\n")
        
        # Получаем все объекты в лоте
        objects = analytics.query(f"""
            SELECT 
                "Город",
                "Наименование объекта",
                "S общая помещений, внутрянка (м2)",
                "S общая территории, внешка (м2)",
                "Затраты закупку ОС (без НДС)"
            FROM cities_areas
            WHERE "Лот №" = {lot_num}
        """)
        
        print(f"📍 ОБЪЕКТЫ В ЛОТЕ (всего: {len(objects)}):\n")
        
        total_equipment_cost = 0
        
        for i, obj in enumerate(objects, 1):
            city = obj[0]
            name = obj[1]
            indoor = obj[2]
            outdoor = obj[3]
            equipment_cost = obj[4] or 0
            
            total_equipment_cost += equipment_cost
            
            print(f"   {i}. {city}")
            print(f"      Объект: {name}")
            if indoor:
                print(f"      Площадь: {indoor} м² (помещения) + {outdoor or 0} м² (территория)")
            print(f"      💰 Затраты на ОС: {equipment_cost:,} руб.")
        
        print(f"\n   {'─'*116}")
        print(f"   💵 ИТОГО затраты на ОС по лоту {lot_num}: {total_equipment_cost:,} руб.\n")
        
        # Получаем детализацию по технике для лота
        print(f"🚜 ТЕХНИКА (ОС) ПО ЛОТУ {lot_num}:\n")
        
        # Названия колонок техники (индексы 10-25) - ТОЧНЫЕ как в БД
        equipment_columns = [
            " МТЗ-82.1, отвал КО-4 гидравлический, щетка МК-2.0, усиленный ковш",
            "Минипогруз-чик (ковш, отвал, щетка) МКСМ  800Н ",
            "МКР-32О (отвал, щетка)",
            "Колесный мини-погрузчик Bobcat S530",
            "КО-806-40 на шасси КАМАЗ-53605-773950-48 ",
            "Фронтальный погрузчик SDLG LG936L (Комплектация: Ковш 2 м3, джойстик, 2-х секционный гидрораспределитель, 2 гидролинии,отвалом для снега)",
            "Камаз 45143-776012-50 Самосвал Евро 5",
            "ВАЗ Лада Ларгус Фургон 2020 (для аварийной службы)",
            "Автобус газель сити 22 сид. Мест",
            "Газель комбинированная  для аварийной службы  Соболь  ЦМФ",
            "Газель фургон   3302  Ефроплатформа",
            "Косилка КРН-2.1 навесная д/трактора МТЗ-82.1",
            "Бочка для полива",
            "Самосваль-ный тракторный прицеп 2ПТС 4,5 ",
            "Полуприцеп-разбрасыватель РС 0.5  ( 3, 3 куба) ",
            "Автовышка ML-45НА шасси КАМАЗ-43118"
        ]
        
        # Получаем количество техники по объектам лота
        equipment_data = analytics.query(f"""
            SELECT 
                "Город",
                "Наименование объекта",
                "{equipment_columns[0]}",
                "{equipment_columns[1]}",
                "{equipment_columns[2]}",
                "{equipment_columns[3]}",
                "{equipment_columns[4]}",
                "{equipment_columns[5]}",
                "{equipment_columns[6]}",
                "{equipment_columns[7]}",
                "{equipment_columns[8]}",
                "{equipment_columns[9]}",
                "{equipment_columns[10]}",
                "{equipment_columns[11]}",
                "{equipment_columns[12]}",
                "{equipment_columns[13]}",
                "{equipment_columns[14]}",
                "{equipment_columns[15]}"
            FROM cities_areas
            WHERE "Лот №" = {lot_num}
        """)
        
        # Суммируем технику по всему лоту
        equipment_totals = {}
        for eq_row in equipment_data:
            for idx, col_name in enumerate(equipment_columns):
                quantity = eq_row[idx + 2]  # +2 т.к. первые 2 колонки - город и объект
                if quantity:
                    try:
                        qty = int(quantity) if quantity else 0
                        if qty > 0:
                            equipment_totals[col_name] = equipment_totals.get(col_name, 0) + qty
                    except (ValueError, TypeError):
                        pass
        
        if equipment_totals:
            for eq_name, qty in sorted(equipment_totals.items(), key=lambda x: x[1], reverse=True):
                # Сокращаем название для читаемости
                short_name = eq_name[:70] + "..." if len(eq_name) > 70 else eq_name
                print(f"   • {short_name:<73} : {qty:>3} шт.")
        else:
            print(f"   Нет данных по технике")
        
        print()


if __name__ == "__main__":
    analyze_lots_structure()
