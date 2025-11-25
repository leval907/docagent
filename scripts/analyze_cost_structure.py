
import pandas as pd
import sys
import os

# Define paths to the CSV files
base_path = '/opt/docagent/data/osv_revenue_0925/input/info_docs/Postgres/correct_2/master_schema_files/'
categories_path = os.path.join(base_path, 'cost_categories.csv')
groups_path = os.path.join(base_path, 'cost_groups.csv')
items_path = os.path.join(base_path, 'cost_items.csv')

print("--- Loading Cost Structure Data ---")

try:
    # Load data
    categories = pd.read_csv(categories_path)
    groups = pd.read_csv(groups_path)
    items = pd.read_csv(items_path)

    print("\n--- Cost Categories ---")
    print(categories.head())
    
    print("\n--- Cost Groups ---")
    print(groups.head())
    
    print("\n--- Cost Items ---")
    print(items.head())

    # Merge to create a full view
    # Assuming standard join keys like category_id, group_id
    # Let's inspect columns first
    print("\n--- Columns ---")
    print(f"Categories: {categories.columns.tolist()}")
    print(f"Groups: {groups.columns.tolist()}")
    print(f"Items: {items.columns.tolist()}")

    # Merge to create a full mapping
    # Items -> Groups -> Categories
    # Note: 'name_ru' from groups will become 'name_ru_x' or similar if not handled, but let's check suffixes
    full_structure = items.merge(groups, left_on='group_id', right_on='id', suffixes=('_item', '_group'))
    # Now full_structure has 'name_ru' from groups (which is 'name_ru_group' effectively due to suffix if collision, or just 'name_ru')
    # Let's check columns after first merge
    # print(full_structure.columns)
    
    full_structure = full_structure.merge(categories, left_on='category_code_group', right_on='code', suffixes=('_group', '_cat'))
    
    # print(full_structure.columns)
    
    # Select relevant columns. 
    # Group name is 'name_ru_group'
    # Category name is 'name_ru_cat' (or 'name_ru' if no collision with previous)
    
    print("\n--- Full Cost Structure Mapping (First 20) ---")
    print(full_structure[['new_code', 'cost_item_name', 'name_ru_group', 'name_ru_cat']].head(20))
    
    # Save mapping to file for reference
    full_structure[['new_code', 'cost_item_name', 'name_ru_group', 'name_ru_cat']].to_csv('/opt/docagent/data/cost_mapping.csv', index=False)
    print("\nMapping saved to /opt/docagent/data/cost_mapping.csv")

except Exception as e:
    print(f"Error loading data: {e}")
