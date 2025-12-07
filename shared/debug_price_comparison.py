#!/usr/bin/env python3
"""
Debug script to test price extraction and comparison
Run this to see exactly what's being extracted
"""

import sys
sys.path.append('shared')

from papl_parser import PAPLParser

# Initialize parser
parser = PAPLParser()

# Parse both documents (update paths to your actual files)
print("=" * 80)
print("PARSING DOCUMENTS")
print("=" * 80)

old_file = "/Users/stusmith/Work/Pricing/Digital-First-Strategy/assets/NDIS Pricing Arrangements and Price Limits 2024-25 v1.3.docx"  # UPDATE THIS
new_file = "/Users/stusmith/Work/Pricing/Digital-First-Strategy/assets/NDIS Pricing Arrangements and Price Limits 2025-26 (1).docx"  # UPDATE THIS

print(f"Parsing OLD: {old_file}")
old_data = parser.parse(old_file)
print(f"✓ Found {len(old_data['raw_tables'])} tables")

print(f"\nParsing NEW: {new_file}")
new_data = parser.parse(new_file)
print(f"✓ Found {len(new_data['raw_tables'])} tables")

# Test with your specific table containing item 04_599_0104_6_1
# You mentioned this is in a "Short Notice Cancellation" table
# Let's find it by looking for tables with this item number

print("\n" + "=" * 80)
print("FINDING TABLE WITH ITEM 04_599_0104_6_1")
print("=" * 80)

target_item = "04_599_0104_6_1"
old_table_idx = None
new_table_idx = None

# Search OLD document
for idx, table in enumerate(old_data['raw_tables']):
    data = table.get('data', [])
    for row in data:
        for cell in row:
            if target_item in str(cell):
                old_table_idx = idx
                print(f"Found in OLD document: Table {idx}")
                break
        if old_table_idx:
            break
    if old_table_idx:
        break

# Search NEW document
for idx, table in enumerate(new_data['raw_tables']):
    data = table.get('data', [])
    for row in data:
        for cell in row:
            if target_item in str(cell):
                new_table_idx = idx
                print(f"Found in NEW document: Table {idx}")
                break
        if new_table_idx:
            break
    if new_table_idx:
        break

if old_table_idx is None or new_table_idx is None:
    print("❌ Could not find table with item 04_599_0104_6_1")
    print(f"   Found in OLD: {old_table_idx}")
    print(f"   Found in NEW: {new_table_idx}")
    sys.exit(1)

# Extract prices from both tables
print("\n" + "=" * 80)
print(f"EXTRACTING PRICES")
print("=" * 80)

old_table = old_data['raw_tables'][old_table_idx]
new_table = new_data['raw_tables'][new_table_idx]

print(f"\nOLD Table {old_table_idx}:")
print(f"  Rows: {old_table.get('row_count')}")
print(f"  Cols: {old_table.get('col_count')}")
if old_table.get('data'):
    print(f"  Headers: {old_table['data'][0][:5]}")

old_prices = parser._extract_prices_from_table(old_table)
print(f"  Extracted prices: {len(old_prices)}")

print(f"\nNEW Table {new_table_idx}:")
print(f"  Rows: {new_table.get('row_count')}")
print(f"  Cols: {new_table.get('col_count')}")
if new_table.get('data'):
    print(f"  Headers: {new_table['data'][0][:5]}")

new_prices = parser._extract_prices_from_table(new_table)
print(f"  Extracted prices: {len(new_prices)}")

# Show details for target item
print("\n" + "=" * 80)
print(f"DETAILS FOR ITEM {target_item}")
print("=" * 80)

print("\nOLD Document:")
old_target_prices = [p for p in old_prices if p['item_number'] == target_item]
if old_target_prices:
    for p in old_target_prices:
        print(f"  Item: {p['item_number']}")
        print(f"  Price: ${p['price']}")
        print(f"  Location: table {p['table_index']}, row {p['row_index']}, col {p['col_index']}")
        print(f"  Raw text: '{p['raw_text']}'")
        print()
else:
    print("  ❌ No prices found for this item")
    # Debug: show what item numbers ARE being extracted
    unique_items = set(p['item_number'] for p in old_prices if p['item_number'])
    print(f"  Found {len(unique_items)} unique item numbers")
    print(f"  Sample items: {list(unique_items)[:5]}")

print("\nNEW Document:")
new_target_prices = [p for p in new_prices if p['item_number'] == target_item]
if new_target_prices:
    for p in new_target_prices:
        print(f"  Item: {p['item_number']}")
        print(f"  Price: ${p['price']}")
        print(f"  Location: table {p['table_index']}, row {p['row_index']}, col {p['col_index']}")
        print(f"  Raw text: '{p['raw_text']}'")
        print()
else:
    print("  ❌ No prices found for this item")
    # Debug: show what item numbers ARE being extracted
    unique_items = set(p['item_number'] for p in new_prices if p['item_number'])
    print(f"  Found {len(unique_items)} unique item numbers")
    print(f"  Sample items: {list(unique_items)[:5]}")

# Try comparison
print("\n" + "=" * 80)
print("COMPARING PRICES")
print("=" * 80)

changes = parser._compare_table_prices(old_table, new_table)
print(f"\nTotal changes detected: {len(changes)}")

if changes:
    print("\n✓ Changes found!")
    for change in changes[:5]:  # Show first 5
        print(f"  Item: {change['item_number']}")
        print(f"  OLD: ${change['old_price']} → NEW: ${change['new_price']}")
        print(f"  Difference: ${change['difference']} ({change['percent_change']:.1f}%)")
        print()
else:
    print("\n❌ No changes detected!")
    print("\nDEBUG: Building item lookup dicts...")
    
    # Manually build the lookup dicts to see what's happening
    old_by_item = {}
    for p in old_prices:
        if p['item_number']:
            if p['item_number'] not in old_by_item:
                old_by_item[p['item_number']] = p
    
    new_by_item = {}
    for p in new_prices:
        if p['item_number']:
            if p['item_number'] not in new_by_item:
                new_by_item[p['item_number']] = p
    
    print(f"  OLD: {len(old_by_item)} unique items")
    print(f"  NEW: {len(new_by_item)} unique items")
    
    # Check for common items
    common_items = set(old_by_item.keys()) & set(new_by_item.keys())
    print(f"  Common items: {len(common_items)}")
    
    if len(common_items) > 0:
        print(f"\nSample common items:")
        for item in list(common_items)[:3]:
            old_p = old_by_item[item]['price']
            new_p = new_by_item[item]['price']
            print(f"    {item}: ${old_p} vs ${new_p} (match: {old_p == new_p})")
    
    # Check specifically for our target item
    if target_item in old_by_item and target_item in new_by_item:
        print(f"\n  Target item {target_item}:")
        print(f"    OLD price: ${old_by_item[target_item]['price']}")
        print(f"    NEW price: ${new_by_item[target_item]['price']}")
        print(f"    Equal? {old_by_item[target_item]['price'] == new_by_item[target_item]['price']}")
        
        # Show actual values
        old_val = old_by_item[target_item]['price']
        new_val = new_by_item[target_item]['price']
        print(f"    OLD type: {type(old_val)}, value: {repr(old_val)}")
        print(f"    NEW type: {type(new_val)}, value: {repr(new_val)}")
    elif target_item not in old_by_item:
        print(f"\n  ❌ Target item {target_item} NOT in old_by_item!")
    elif target_item not in new_by_item:
        print(f"\n  ❌ Target item {target_item} NOT in new_by_item!")

print("\n" + "=" * 80)
print("DEBUG COMPLETE")
print("=" * 80)
