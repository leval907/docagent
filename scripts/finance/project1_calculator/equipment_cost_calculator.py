#!/usr/bin/env python3
"""
Расчет детальной стоимости ОС (техники) по каждому лоту
Связывает количество из cities_areas с ценами из equipment
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from scripts.analytics.duckdb_analytics import DuckDBAnalytics


# Маппинг: название колонки в cities_areas → номер строки в equipment
EQUIPMENT_MAPPING = {
    " МТЗ-82.1, отвал КО-4 гидравлический, щетка МК-2.0, усиленный ковш": "1",
    "МКР-32О (отвал, щетка)": "2",
    "Колесный мини-погрузчик Bobcat S530": "6",
    "КО-806-40 на шасси КАМАЗ-53605-773950-48 ": "7",
    "Фронтальный погрузчик SDLG LG936L (Комплектация: Ковш 2 м3, джойстик, 2-х секционный гидрораспределитель, 2 гидролинии,отвалом для снега)": "3",
    "Камаз 45143-776012-50 Самосвал Евро 5": None,  # Нет в справочнике
    "ВАЗ Лада Ларгус Фургон 2020 (для аварийной службы)": None,
    "Автобус газель сити 22 сид. Мест": "8",
    "Газель комбинированная  для аварийной службы  Соболь  ЦМФ": "10",
    "Газель фургон   3302  Ефроплатформа": "9",
    "Косилка КРН-2.1 навесная д/трактора МТЗ-82.1": None,
    "Бочка для полива": None,
    "Самосваль-ный тракторный прицеп 2ПТС 4,5 ": None,
    "Полуприцеп-разбрасыватель РС 0.5  ( 3, 3 куба) ": None,
    "Автовышка ML-45НА шасси КАМАЗ-43118": None,
    "Минипогруз-чик (ковш, отвал, щетка) МКСМ  800Н ": "5"
}


def calculate_equipment_costs():
    """Рассчитывает детальную стоимость ОС по лотам"""
    
    db_path = "knowledge_base/duckdb/calculator/project1_calculator.duckdb"
    analytics = DuckDBAnalytics(db_path)
    
    print("\n" + "="*120)
    print("💰 ДЕТАЛЬНЫЙ РАСЧЕТ СТОИМОСТИ ОСНОВНЫХ СРЕДСТВ (ТЕХНИКА)")
    print("="*120 + "\n")
    
    # Получаем справочник техники
    equipment_catalog = {}
    equipment_rows = analytics.query("""
        SELECT Field1, Field2, Field4, Field11, Field12, Field13, Field14, Field15, 
               Field16, Field17, Field18, Field19, Field20, Field21
        FROM equipment
        WHERE Field1 IS NOT NULL AND Field1 != ''
    """)
    
    for row in equipment_rows:
        eq_id = row[0]
        equipment_catalog[eq_id] = {
            'name': row[1],
            'price': int(row[2]) if row[2] else 0,
            'delivery': {
                'Тобольск': int(row[3]) if row[3] else 0,
                'Благовещенск': int(row[4]) if row[4] else 0,
                'Красноярск': int(row[5]) if row[5] else 0,
                'Томск': int(row[6]) if row[6] else 0,
                'Нижний Новгород': int(row[7]) if row[7] else 0,
                'Пермь': int(row[8]) if row[8] else 0,
                'Воронеж': int(row[9]) if row[9] else 0,
                'Курск': int(row[10]) if row[10] else 0,
                'Новокуйбышевск': int(row[11]) if row[11] else 0,
                'Усть-Луга': int(row[12]) if row[12] else 0,
                'Тверь': int(row[13]) if row[13] else 0,
            }
        }
    
    # Получаем лоты
    lots = analytics.query("""
        SELECT DISTINCT "Лот №"
        FROM cities_areas
        WHERE "Лот №" IS NOT NULL
        ORDER BY "Лот №"
    """)
    
    total_calculated = 0
    total_declared = 0
    
    for lot_row in lots:
        lot_num = lot_row[0]
        
        # Получаем данные лота
        lot_data = analytics.query(f"""
            SELECT 
                "Город",
                "Наименование объекта",
                "Затраты закупку ОС (без НДС)",
                "{list(EQUIPMENT_MAPPING.keys())[0]}",
                "{list(EQUIPMENT_MAPPING.keys())[1]}",
                "{list(EQUIPMENT_MAPPING.keys())[2]}",
                "{list(EQUIPMENT_MAPPING.keys())[3]}",
                "{list(EQUIPMENT_MAPPING.keys())[4]}",
                "{list(EQUIPMENT_MAPPING.keys())[5]}",
                "{list(EQUIPMENT_MAPPING.keys())[6]}",
                "{list(EQUIPMENT_MAPPING.keys())[7]}",
                "{list(EQUIPMENT_MAPPING.keys())[8]}",
                "{list(EQUIPMENT_MAPPING.keys())[9]}",
                "{list(EQUIPMENT_MAPPING.keys())[10]}",
                "{list(EQUIPMENT_MAPPING.keys())[11]}",
                "{list(EQUIPMENT_MAPPING.keys())[12]}",
                "{list(EQUIPMENT_MAPPING.keys())[13]}",
                "{list(EQUIPMENT_MAPPING.keys())[14]}",
                "{list(EQUIPMENT_MAPPING.keys())[15]}"
            FROM cities_areas
            WHERE "Лот №" = {lot_num}
            LIMIT 1
        """)
        
        if not lot_data:
            continue
            
        city = lot_data[0][0]
        obj_name = lot_data[0][1]
        declared_cost = lot_data[0][2] or 0
        
        print(f"{'='*120}")
        print(f"🏢 ЛОТ {lot_num}: {city}")
        print(f"   Объект: {obj_name}")
        print(f"{'='*120}\n")
        print(f"   💵 Заявленная стоимость ОС: {declared_cost:,} руб. (без НДС)\n")
        
        # Определяем город для доставки (упрощенно по первому слову)
        city_key = None
        for key in equipment_catalog.get('1', {}).get('delivery', {}).keys():
            if key.lower() in city.lower():
                city_key = key
                break
        
        print(f"   🚚 Город доставки: {city_key or 'не определен'}\n")
        print(f"   {'─'*116}")
        print(f"   {'ТЕХНИКА':<50} {'КОЛ-ВО':>8} {'ЦЕНА (НДС)':>15} {'ДОСТАВКА':>12} {'СУММА':>15}")
        print(f"   {'─'*116}")
        
        calculated_cost = 0
        
        for idx, (col_name, eq_id) in enumerate(EQUIPMENT_MAPPING.items()):
            quantity = lot_data[0][idx + 3]  # +3 т.к. первые 3 колонки - город, объект, стоимость
            
            if not quantity or quantity == 0:
                continue
            
            # Обработка текстовых значений типа "1 аренда"
            try:
                qty = int(str(quantity).split()[0])  # Берем только первое число
            except (ValueError, AttributeError):
                continue
            
            if eq_id and eq_id in equipment_catalog:
                eq = equipment_catalog[eq_id]
                price = eq['price']
                delivery = eq['delivery'].get(city_key, 0) if city_key else 0
                
                # Цена с НДС, переводим в без НДС
                price_no_vat = int(price / 1.2)
                
                item_cost = (price_no_vat + delivery) * qty
                calculated_cost += item_cost
                
                # Сокращаем название
                short_name = eq['name'][:47] + "..." if len(eq['name']) > 50 else eq['name']
                
                print(f"   {short_name:<50} {qty:>8} {price_no_vat:>15,} {delivery:>12,} {item_cost:>15,}")
            else:
                # Техника не найдена в справочнике
                short_name = col_name[:47] + "..." if len(col_name) > 50 else col_name
                print(f"   {short_name:<50} {qty:>8} {'N/A':>15} {'N/A':>12} {'N/A':>15}")
        
        print(f"   {'─'*116}")
        print(f"   {'ИТОГО рассчитано:':<50} {' ':>8} {' ':>15} {' ':>12} {calculated_cost:>15,}")
        print(f"   {'ЗАЯВЛЕНО:':<50} {' ':>8} {' ':>15} {' ':>12} {declared_cost:>15,}")
        
        diff = calculated_cost - declared_cost
        diff_pct = (diff / declared_cost * 100) if declared_cost > 0 else 0
        
        if abs(diff_pct) < 5:
            status = "✅ Совпадает"
        elif diff_pct > 0:
            status = f"⚠️  Превышение на {diff_pct:.1f}%"
        else:
            status = f"⬇️  Ниже на {abs(diff_pct):.1f}%"
        
        print(f"   {'РАЗНИЦА:':<50} {' ':>8} {' ':>15} {' ':>12} {diff:>15,}  {status}")
        print()
        
        total_calculated += calculated_cost
        total_declared += declared_cost
    
    # Итоговая сводка
    print("="*120)
    print("📊 ИТОГОВАЯ СВОДКА ПО ВСЕМ ЛОТАМ")
    print("="*120)
    print(f"\n   Рассчитанная стоимость ОС:  {total_calculated:>20,} руб.")
    print(f"   Заявленная стоимость ОС:    {total_declared:>20,} руб.")
    print(f"   Разница:                    {total_calculated - total_declared:>20,} руб.")
    
    if total_declared > 0:
        diff_pct = ((total_calculated - total_declared) / total_declared * 100)
        print(f"   Отклонение:                 {diff_pct:>20.1f}%")
    
    print("\n" + "="*120 + "\n")


if __name__ == "__main__":
    calculate_equipment_costs()
