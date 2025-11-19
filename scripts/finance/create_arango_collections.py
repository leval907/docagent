#!/usr/bin/env python3
"""
Создание коллекций в ArangoDB для графового представления проекта калькулятора
"""

from pyArango.connection import Connection
import sys

# Подключение к ArangoDB (через Docker network)
try:
    conn = Connection(
        arangoURL='http://localhost:8529',
        username='root',
        password='openSesame'
    )
    print("✅ Подключено к ArangoDB")
except Exception as e:
    print(f"❌ Ошибка подключения: {e}")
    print("Попробую через Docker exec...")
    sys.exit(1)

# Создаем или используем существующую БД
db_name = "project1_calculator"

if db_name in conn.databases:
    db = conn[db_name]
    print(f"📂 Используется существующая БД: {db_name}")
else:
    db = conn.createDatabase(name=db_name)
    print(f"📂 Создана новая БД: {db_name}")

print("\n" + "="*80)
print("🏗️  СОЗДАНИЕ КОЛЛЕКЦИЙ")
print("="*80 + "\n")

# Коллекции документов (вершины графа)
document_collections = {
    'lots': 'Лоты (тендерные участки)',
    'objects': 'Объекты СИБУР (предприятия)',
    'cities': 'Города',
    'equipment_types': 'Типы техники',
    'equipment_items': 'Единицы техники',
    'costs': 'Затраты (ФОТ, прочие, ОС)',
    'contracts': 'Контракты (5 лет)'
}

# Коллекции рёбер (связи в графе)
edge_collections = {
    'lot_includes_object': 'Лот включает объект',
    'object_located_in_city': 'Объект находится в городе',
    'object_requires_equipment': 'Объект требует технику',
    'equipment_has_cost': 'Техника имеет стоимость',
    'lot_has_contract': 'Лот имеет контракт',
    'contract_has_costs': 'Контракт содержит затраты'
}

# Создаём коллекции документов
for coll_name, description in document_collections.items():
    if db.hasCollection(coll_name):
        print(f"   ✓ {coll_name:<20} уже существует - {description}")
    else:
        db.createCollection(name=coll_name)
        print(f"   + {coll_name:<20} создана - {description}")

print()

# Создаём коллекции рёбер
for coll_name, description in edge_collections.items():
    if db.hasCollection(coll_name):
        print(f"   ✓ {coll_name:<30} уже существует - {description}")
    else:
        db.createCollection(className='Edges', name=coll_name)
        print(f"   + {coll_name:<30} создана - {description}")

# Создаём граф
graph_name = "project1_graph"

print(f"\n{'='*80}")
print(f"🕸️  СОЗДАНИЕ ГРАФА: {graph_name}")
print(f"{'='*80}\n")

if db.hasGraph(graph_name):
    print(f"   ✓ Граф '{graph_name}' уже существует")
else:
    graph = db.createGraph(graph_name)
    
    # Добавляем определения рёбер в граф
    graph.createEdgeDefinition(
        edgeName='lot_includes_object',
        fromCollections=['lots'],
        toCollections=['objects']
    )
    
    graph.createEdgeDefinition(
        edgeName='object_located_in_city',
        fromCollections=['objects'],
        toCollections=['cities']
    )
    
    graph.createEdgeDefinition(
        edgeName='object_requires_equipment',
        fromCollections=['objects'],
        toCollections=['equipment_items']
    )
    
    graph.createEdgeDefinition(
        edgeName='equipment_has_cost',
        fromCollections=['equipment_items'],
        toCollections=['costs']
    )
    
    graph.createEdgeDefinition(
        edgeName='lot_has_contract',
        fromCollections=['lots'],
        toCollections=['contracts']
    )
    
    graph.createEdgeDefinition(
        edgeName='contract_has_costs',
        fromCollections=['contracts'],
        toCollections=['costs']
    )
    
    print(f"   + Граф '{graph_name}' создан с 6 типами рёбер")

print(f"\n{'='*80}")
print("✅ СТРУКТУРА СОЗДАНА!")
print(f"{'='*80}\n")

print("📊 Структура графа:\n")
print("   Лоты → включают → Объекты")
print("   Объекты → находятся в → Городах")
print("   Объекты → требуют → Технику")
print("   Техника → имеет → Стоимость")
print("   Лоты → имеют → Контракты")
print("   Контракты → содержат → Затраты")

print(f"\n💡 Примеры запросов:\n")
print("   1. Какая техника используется в Тобольске?")
print("   2. Какие лоты имеют максимальную стоимость ОС?")
print("   3. Какие города требуют больше всего техники определённого типа?")
print("   4. Какова полная цепочка затрат от лота до единицы техники?")

print(f"\n🌐 Веб-интерфейс: http://localhost:8529")
print(f"   БД: {db_name}")
print(f"   User: root")
print(f"   Password: openSesame\n")
