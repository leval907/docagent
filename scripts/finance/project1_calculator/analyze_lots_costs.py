#!/usr/bin/env python3
"""
Анализ структуры затрат по лотам для Проекта 1 (СИБУР)
"""

import sys
from pathlib import Path

# Добавляем путь к модулям
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from scripts.analytics.duckdb_analytics import DuckDBAnalytics


def analyze_lots_costs():
    """Анализирует структуру затрат по каждому лоту"""
    
    db_path = "knowledge_base/duckdb/calculator/project1_calculator.duckdb"
    analytics = DuckDBAnalytics(db_path)
    
    print("\n" + "="*120)
    print("📊 ДЕТАЛЬНЫЙ АНАЛИЗ ЗАТРАТ ПО ЛОТАМ")
    print("="*120 + "\n")
    
    # Получаем данные по лотам
    lots = analytics.query("""
        SELECT 
            "Лот №",
            "Город",
            "Наименование объекта",
            "Расчетная выручка в первый ЗИМНИЙ месяц без НДС (без учета индексации в последние 3 года)",
            "Затраты на производственный персонал (ФОТ с отчислениями, питание (только вахта)) за первый ЗИМНИЙ месяц.",
            "Первичные вложения в ""прочее (в т.ч.: РМ и ПГР, субподряд, инвентарь, спецодежда, прочее)"" (за первый ЗИМНИЙ месяц, без учета закупки ОС, без НДС)",
            "Затраты закупку ОС (без НДС)",
            "Поданая стоимость услуг за весь период договора - 5 лет, без НДС (с учетом всех затрат - из ТКП на переторжке)"
        FROM cities_areas
        WHERE "Лот №" IS NOT NULL
        ORDER BY "Лот №"
    """)
    
    total_revenue = 0
    total_fot = 0
    total_other = 0
    total_equipment = 0
    total_contract = 0
    
    for lot in lots:
        lot_num = lot[0]
        city = lot[1]
        name = lot[2]
        revenue = lot[3] or 0
        fot = lot[4] or 0
        other = lot[5] or 0
        equipment = lot[6] or 0
        contract = lot[7] or 0
        
        # Накопление итогов
        total_revenue += revenue
        total_fot += fot
        total_other += other
        total_equipment += equipment
        total_contract += contract
        
        # Расчеты
        monthly_costs = fot + other
        margin_month = revenue - monthly_costs
        margin_pct = (margin_month / revenue * 100) if revenue > 0 else 0
        
        # Доли затрат
        fot_share = (fot / revenue * 100) if revenue > 0 else 0
        other_share = (other / revenue * 100) if revenue > 0 else 0
        
        print(f"🏢 ЛОТ {lot_num}: {city[:60]}")
        print(f"   Объект: {name}")
        print(f"   {'-'*116}")
        print(f"   📈 Выручка (зимний месяц):             {revenue:>15,} руб. (100.0%)")
        print(f"   👥 ФОТ персонал:                       {fot:>15,} руб. ({fot_share:>5.1f}%)")
        print(f"   🔧 Прочие расходы (РМ, субподряд):     {other:>15,.0f} руб. ({other_share:>5.1f}%)")
        print(f"   {'─'*116}")
        print(f"   💵 Операционные затраты (месяц):       {monthly_costs:>15,.0f} руб.")
        print(f"   📊 Маржа (зимний месяц):               {margin_month:>15,.0f} руб. ({margin_pct:>5.1f}%)")
        print(f"   {'─'*116}")
        print(f"   🚜 Закупка ОС (единоразово):           {equipment:>15,} руб.")
        print(f"   💰 Контракт 5 лет (общая стоимость):   {contract:>15,.0f} руб.")
        print()
    
    # Итоговые показатели
    print("="*120)
    print("📋 СВОДНЫЕ ПОКАЗАТЕЛИ ПО ВСЕМ ЛОТАМ")
    print("="*120)
    
    total_monthly_costs = total_fot + total_other
    total_margin = total_revenue - total_monthly_costs
    total_margin_pct = (total_margin / total_revenue * 100) if total_revenue > 0 else 0
    
    print(f"\n💰 ФИНАНСЫ ЗА ЗИМНИЙ МЕСЯЦ:")
    print(f"   Общая выручка:                         {total_revenue:>15,} руб. (100.0%)")
    print(f"   - ФОТ персонал:                        {total_fot:>15,} руб. ({total_fot/total_revenue*100:>5.1f}%)")
    print(f"   - Прочие расходы:                      {total_other:>15,.0f} руб. ({total_other/total_revenue*100:>5.1f}%)")
    print(f"   {'─'*116}")
    print(f"   = Операционные затраты:                {total_monthly_costs:>15,.0f} руб.")
    print(f"   = Маржа:                               {total_margin:>15,.0f} руб. ({total_margin_pct:>5.1f}%)")
    
    print(f"\n🚜 КАПИТАЛЬНЫЕ ВЛОЖЕНИЯ:")
    print(f"   Закупка ОС (единоразово):              {total_equipment:>15,} руб.")
    
    print(f"\n📊 КОНТРАКТ 5 ЛЕТ:")
    print(f"   Общая стоимость:                       {total_contract:>15,.0f} руб.")
    print(f"   Средняя стоимость в год:               {total_contract/5:>15,.0f} руб.")
    print(f"   Средняя стоимость в месяц:             {total_contract/60:>15,.0f} руб.")
    
    # Анализ структуры
    print(f"\n🔍 СТРУКТУРА ЗАТРАТ (от выручки зимнего месяца):")
    print(f"   ФОТ:                                   {total_fot/total_revenue*100:>6.1f}%")
    print(f"   Прочие расходы:                        {total_other/total_revenue*100:>6.1f}%")
    print(f"   Маржа:                                 {total_margin_pct:>6.1f}%")
    
    print("\n" + "="*120 + "\n")


if __name__ == "__main__":
    analyze_lots_costs()
