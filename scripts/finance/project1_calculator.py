#!/usr/bin/env python3
"""
Калькулятор для Проекта 1
Расчет стоимости контракта по обслуживанию объектов
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from scripts.analytics.duckdb_analytics import DuckDBAnalytics

class ContractCalculator:
    def __init__(self):
        """Инициализация калькулятора"""
        db_path = "knowledge_base/duckdb/calculator/project1_calculator.duckdb"
        self.analytics = DuckDBAnalytics(db_path)
    
    def get_objects_summary(self):
        """Получает сводку по всем объектам"""
        return self.analytics.query("""
            SELECT 
                "Лот №" as lot_number,
                "Город" as city,
                "Наименование объекта" as object_name,
                CASE 
                    WHEN "S общая помещений, внутрянка (м2)" IS NULL 
                        OR "S общая помещений, внутрянка (м2)" = 'None' THEN 0
                    WHEN "S общая помещений, внутрянка (м2)" LIKE '%/%' THEN
                        CAST(
                            replace(
                                regexp_replace(
                                    split_part("S общая помещений, внутрянка (м2)", '/', 1),
                                    '[^0-9,]', '', 'g'
                                ),
                                ',', '.'
                            ) AS FLOAT
                        )
                    ELSE 
                        CAST("S общая помещений, внутрянка (м2)" AS FLOAT)
                END as indoor_area,
                COALESCE("S общая территории, внешка (м2)", 0) as outdoor_area,
                COALESCE("Расчетная выручка в первый ЗИМНИЙ месяц без НДС (без учета индексации в последние 3 года)", 0) as monthly_revenue,
                COALESCE("Поданая стоимость услуг за весь период договора - 5 лет, без НДС (с учетом всех затрат - из ТКП на переторжке)", 0) as contract_5years
            FROM cities_areas
            ORDER BY lot_number
        """)
    
    def calculate_total_areas(self):
        """Рассчитывает общие площади по всем объектам"""
        result = self.analytics.query("""
            SELECT 
                COUNT(*) as total_objects,
                SUM(
                    CASE 
                        WHEN "S общая помещений, внутрянка (м2)" IS NULL 
                            OR "S общая помещений, внутрянка (м2)" = 'None' THEN 0
                        WHEN "S общая помещений, внутрянка (м2)" LIKE '%/%' THEN
                            -- Для значений типа "173 475,92 / 321 68,36" берем первое число
                            CAST(
                                replace(
                                    regexp_replace(
                                        split_part("S общая помещений, внутрянка (м2)", '/', 1),
                                        '[^0-9,]', '', 'g'
                                    ),
                                    ',', '.'
                                ) AS FLOAT
                            )
                        ELSE 
                            CAST("S общая помещений, внутрянка (м2)" AS FLOAT)
                    END
                ) as total_indoor,
                SUM(COALESCE("S общая территории, внешка (м2)", 0)) as total_outdoor
            FROM cities_areas
        """)
        return result[0] if result else {}
    
    def get_equipment_list(self):
        """Получить список техники"""
        result = self.analytics.query("""
            SELECT * FROM equipment
            WHERE Field1 IS NOT NULL
            LIMIT 20
        """)
        
        return result
    
    def create_calculator_report(self):
        """Создать калькулятор для заказчика"""
        
        print("\n" + "="*80)
        print("📊 КАЛЬКУЛЯТОР СТОИМОСТИ КОНТРАКТА")
        print("Проект: Обслуживание объектов СИБУР")
        print("="*80)
        
        # 1. Общая информация
        totals_result = self.calculate_total_areas()
        if totals_result:
            totals = {
                'total_objects': totals_result[0],
                'total_indoor': totals_result[1],
                'total_outdoor': totals_result[2]
            }
        else:
            totals = {'total_objects': 0, 'total_indoor': 0, 'total_outdoor': 0}
            
        print(f"\n1️⃣ ОБЩАЯ ИНФОРМАЦИЯ:")
        print(f"   Количество объектов: {totals['total_objects']}")
        print(f"   Общая внутренняя площадь: {totals['total_indoor']:,.2f} м²")
        print(f"   Общая внешняя площадь: {totals['total_outdoor']:,.2f} м²")
        print(f"   Всего площади: {totals['total_indoor'] + totals['total_outdoor']:,.2f} м²")
        
        # 2. Разбивка по объектам
        print(f"\n2️⃣ ОБЪЕКТЫ ПО ЛОТАМ:")
        objects = self.get_objects_summary()
        
        total_revenue = 0
        total_contract = 0
        
        for obj in objects:
            lot = obj[0]  # lot_number
            city = obj[1]  # city
            name = obj[2]  # object_name
            indoor = obj[3] or 0  # indoor_area
            outdoor = obj[4] or 0  # outdoor_area
            revenue = obj[5] or 0  # monthly_revenue
            contract = obj[6] or 0  # contract_5years
            
            print(f"\n   Лот {lot}: {city}")
            print(f"   {'━' * 70}")
            print(f"   Объект: {name}")
            print(f"   Площадь внутренняя: {indoor:,.2f} м²")
            print(f"   Площадь внешняя: {outdoor:,.2f} м²")
            print(f"   Выручка (зимний месяц): {revenue:,.0f} руб.")
            print(f"   Стоимость контракта (5 лет): {contract:,.0f} руб.")
            
            total_revenue += revenue
            total_contract += contract
        
        # 3. Итоги
        print(f"\n3️⃣ ИТОГОВЫЕ ПОКАЗАТЕЛИ:")
        print(f"   {'━' * 70}")
        print(f"   Общая выручка (1 зимний месяц): {total_revenue:,.0f} руб.")
        print(f"   Годовая выручка (x12): {total_revenue * 12:,.0f} руб.")
        print(f"   Стоимость контракта (5 лет): {total_contract:,.0f} руб.")
        print(f"   Средняя стоимость в год: {total_contract / 5:,.0f} руб.")
        
        # 4. Расчет на м²
        total_area = totals['total_indoor'] + totals['total_outdoor']
        if total_area > 0:
            price_per_m2_month = total_revenue / total_area
            price_per_m2_year = (total_contract / 5) / total_area
            
            print(f"\n4️⃣ СТОИМОСТЬ НА ЕДИНИЦУ ПЛОЩАДИ:")
            print(f"   {'━' * 70}")
            print(f"   Цена за м² (зимний месяц): {price_per_m2_month:.2f} руб/м²")
            print(f"   Цена за м² в год: {price_per_m2_year:.2f} руб/м²")
        
        print(f"\n{'='*80}\n")
        
        # Экспорт в Excel с использованием pandas
        print("💾 Экспорт данных в Excel...")
        import pandas as pd
        
        # Конвертируем результаты в DataFrame
        df = pd.DataFrame(objects, columns=[
            'Лот №', 'Город', 'Наименование объекта', 
            'Площадь внутр. (м²)', 'Площадь внеш. (м²)',
            'Выручка зимний месяц (руб)', 'Контракт 5 лет (руб)'
        ])
        
        output_path = "knowledge_base/duckdb/calculator/calculator_report.xlsx"
        df.to_excel(output_path, index=False, engine='openpyxl')
        print(f"   ✅ Сохранено: {output_path}")
        
        return {
            'total_revenue_month': total_revenue,
            'total_revenue_year': total_revenue * 12,
            'total_contract_5years': total_contract,
            'total_area': total_area,
            'price_per_m2_month': total_revenue / total_area if total_area > 0 else 0
        }

if __name__ == "__main__":
    calculator = ContractCalculator()
    results = calculator.create_calculator_report()
