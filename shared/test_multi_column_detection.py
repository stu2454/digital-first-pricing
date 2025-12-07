#!/usr/bin/env python3
"""
Test multi-column price detection
Verify that all 3 price columns (National, Remote, Very Remote) are detected
"""

import sys
sys.path.append('shared')

from papl_parser import PAPLParser

parser = PAPLParser()

# Parse documents
print("=" * 80)
print("MULTI-COLUMN PRICE DETECTION TEST")
print("=" * 80)

old_file = "/Users/stusmith/Work/Pricing/Digital-First-Strategy/assets/NDIS Pricing Arrangements and Price Limits 2024-25 v1.3.docx"
new_file = "/Users/stusmith/Work/Pricing/Digital-First-Strategy/assets/NDIS Pricing Arrangements and Price Limits 2025-26 (1).docx"

print(f"\nParsing OLD: {old_file}")
old_data = parser.parse(old_file)

print(f"Parsing NEW: {new_file}")
new_data = parser.parse(new_file)

# Find table with item 01_134_0117_8_1 (Stuart's example)
target_item = "01_134_0117_8_1"
old_table_idx = None
new_table_idx = None

print(f"\n" + "=" * 80)
print(f"FINDING TABLE WITH {target_item}")
print("=" * 80)

for idx, table in enumerate(old_data['raw_tables']):
    for row in table.get('data', []):
        if any(target_item in str(cell) for cell in row):
            old_table_idx = idx
            print(f"Found in OLD: Table {idx}")
            break
    if old_table_idx:
        break

for idx, table in enumerate(new_data['raw_tables']):
    for row in table.get('data', []):
        if any(target_item in str(cell) for cell in row):
            new_table_idx = idx
            print(f"Found in NEW: Table {idx}")
            break
    if new_table_idx:
        break

if old_table_idx is None or new_table_idx is None:
    print(f"❌ Could not find table with {target_item}")
    sys.exit(1)

# Extract prices
old_table = old_data['raw_tables'][old_table_idx]
new_table = new_data['raw_tables'][new_table_idx]

print(f"\n" + "=" * 80)
print("EXTRACTING PRICES")
print("=" * 80)

old_prices = parser._extract_prices_from_table(old_table)
new_prices = parser._extract_prices_from_table(new_table)

print(f"\nOLD table: {len(old_prices)} prices extracted")
print(f"NEW table: {len(new_prices)} prices extracted")

# Show ALL prices for target item
print(f"\n" + "=" * 80)
print(f"ALL PRICES FOR {target_item}")
print("=" * 80)

old_target = [p for p in old_prices if p['item_number'] == target_item]
new_target = [p for p in new_prices if p['item_number'] == target_item]

print(f"\nOLD document ({len(old_target)} prices):")
for p in old_target:
    col_name = {3: 'National', 4: 'Remote', 5: 'Very Remote'}.get(p['col_index'], f"Col {p['col_index']}")
    print(f"  {col_name:12} (col {p['col_index']}): ${p['price']}")

print(f"\nNEW document ({len(new_target)} prices):")
for p in new_target:
    col_name = {3: 'National', 4: 'Remote', 5: 'Very Remote'}.get(p['col_index'], f"Col {p['col_index']}")
    print(f"  {col_name:12} (col {p['col_index']}): ${p['price']}")

# Test comparison
print(f"\n" + "=" * 80)
print("TESTING COMPARISON")
print("=" * 80)

changes = parser._compare_table_prices(old_table, new_table)
print(f"\nTotal changes detected: {len(changes)}")

# Show changes for target item
target_changes = [c for c in changes if c['item_number'] == target_item]
print(f"Changes for {target_item}: {len(target_changes)}")

if target_changes:
    print(f"\n✅ DETECTED CHANGES:")
    for c in target_changes:
        col_name = {3: 'National', 4: 'Remote', 5: 'Very Remote'}.get(c['new_location']['col'], f"Col {c['new_location']['col']}")
        print(f"  {col_name:12}: ${c['old_price']} → ${c['new_price']} (${c['difference']:+.2f}, {c['percent_change']:+.1f}%)")
else:
    print(f"\n❌ NO CHANGES DETECTED!")

# Expected vs Actual
print(f"\n" + "=" * 80)
print("VERIFICATION")
print("=" * 80)

expected_changes = {
    'National': (77.00, 80.06),
    'Remote': (107.80, 112.08),
    'Very Remote': (115.50, 120.09)
}

print(f"\nExpected changes for {target_item}:")
for col_name, (old_val, new_val) in expected_changes.items():
    diff = new_val - old_val
    pct = (diff / old_val) * 100
    print(f"  {col_name:12}: ${old_val} → ${new_val} (${diff:+.2f}, {pct:+.1f}%)")

print(f"\n{'✅ PASS' if len(target_changes) == 3 else '❌ FAIL'}: Expected 3 changes, got {len(target_changes)}")

# Debug: Check the lookup dictionaries
print(f"\n" + "=" * 80)
print("DEBUG: LOOKUP DICTIONARIES")
print("=" * 80)

# Manually build lookup to see what keys are created
old_by_item_col = {}
for p in old_prices:
    if p['item_number']:
        key = (p['item_number'], p['col_index'])
        old_by_item_col[key] = p

new_by_item_col = {}
for p in new_prices:
    if p['item_number']:
        key = (p['item_number'], p['col_index'])
        new_by_item_col[key] = p

# Show keys for target item
old_keys = [k for k in old_by_item_col.keys() if k[0] == target_item]
new_keys = [k for k in new_by_item_col.keys() if k[0] == target_item]

print(f"\nOLD keys for {target_item}:")
for key in old_keys:
    item, col = key
    price = old_by_item_col[key]['price']
    col_name = {3: 'National', 4: 'Remote', 5: 'Very Remote'}.get(col, f"Col {col}")
    print(f"  {key} → ${price} ({col_name})")

print(f"\nNEW keys for {target_item}:")
for key in new_keys:
    item, col = key
    price = new_by_item_col[key]['price']
    col_name = {3: 'National', 4: 'Remote', 5: 'Very Remote'}.get(col, f"Col {col}")
    print(f"  {key} → ${price} ({col_name})")

# Check which keys match
common_keys = set(old_keys) & set(new_keys)
print(f"\nCommon keys (will be compared): {len(common_keys)}")
for key in common_keys:
    item, col = key
    old_price = old_by_item_col[key]['price']
    new_price = new_by_item_col[key]['price']
    col_name = {3: 'National', 4: 'Remote', 5: 'Very Remote'}.get(col, f"Col {col}")
    differs = "CHANGED" if old_price != new_price else "SAME"
    print(f"  {key}: ${old_price} vs ${new_price} ({col_name}) - {differs}")

print(f"\n" + "=" * 80)
print("TEST COMPLETE")
print("=" * 80)
