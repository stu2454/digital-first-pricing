#!/usr/bin/env python3
"""
Test script for price detection functionality

Run this locally to test the price detection fixes before deploying to Render

Usage:
    python test_price_detection.py old_papl.docx new_papl.docx
"""

import sys
import os

# Add shared modules to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'shared'))

from papl_parser import PAPLParser
from semantic_comparer import SemanticComparer


def test_price_extraction():
    """Test basic price extraction"""
    print("=" * 80)
    print("TEST 1: Price Extraction")
    print("=" * 80)
    
    parser = PAPLParser()
    
    test_cases = [
        ("Price: $50.00", 50.0),
        ("$1,234.56 per hour", 1234.56),
        ("Cost is $100", 100.0),
        ("No price here", None),
        ("$50 to $100 range", 50.0),  # Should get first price
    ]
    
    passed = 0
    failed = 0
    
    for text, expected in test_cases:
        result = parser.extract_price(text)
        status = "✅ PASS" if result == expected else "❌ FAIL"
        
        if result == expected:
            passed += 1
        else:
            failed += 1
        
        print(f"{status}: extract_price('{text}') = {result} (expected {expected})")
    
    print(f"\nResults: {passed} passed, {failed} failed")
    return failed == 0


def test_item_number_extraction():
    """Test item number extraction"""
    print("\n" + "=" * 80)
    print("TEST 2: Item Number Extraction")
    print("=" * 80)
    
    parser = PAPLParser()
    
    test_cases = [
        ("01_001_0103_1_1 - Standard Consultation", "01_001_0103_1_1"),
        ("Support item: 01_001_0103", "01_001_0103"),
        ("Item 01_001", "01_001"),
        ("No item number here", None),
    ]
    
    passed = 0
    failed = 0
    
    for text, expected in test_cases:
        result = parser.extract_item_number(text)
        status = "✅ PASS" if result == expected else "❌ FAIL"
        
        if result == expected:
            passed += 1
        else:
            failed += 1
        
        print(f"{status}: extract_item_number('{text}') = {result} (expected {expected})")
    
    print(f"\nResults: {passed} passed, {failed} failed")
    return failed == 0


def test_pricing_table_detection():
    """Test pricing table detection"""
    print("\n" + "=" * 80)
    print("TEST 3: Pricing Table Detection")
    print("=" * 80)
    
    parser = PAPLParser()
    
    # Mock table with pricing data
    pricing_table = {
        'index': 0,
        'data': [
            ['Item Number', 'Description', 'Price'],
            ['01_001', 'Standard Consultation', '$50.00'],
            ['01_002', 'Extended Consultation', '$75.00'],
        ]
    }
    
    # Mock table without pricing data
    non_pricing_table = {
        'index': 1,
        'data': [
            ['Section', 'Description'],
            ['1.1', 'Introduction text here'],
            ['1.2', 'More guidance text'],
        ]
    }
    
    is_pricing, confidence = parser.is_pricing_table(pricing_table)
    print(f"Pricing table: is_pricing={is_pricing}, confidence={confidence}")
    print(f"  ✅ PASS" if is_pricing else "  ❌ FAIL - Should detect as pricing table")
    
    is_pricing, confidence = parser.is_pricing_table(non_pricing_table)
    print(f"Non-pricing table: is_pricing={is_pricing}, confidence={confidence}")
    print(f"  ✅ PASS" if not is_pricing else "  ❌ FAIL - Should NOT detect as pricing table")
    
    return True


def test_price_comparison(old_docx_path, new_docx_path):
    """Test price comparison with real documents"""
    print("\n" + "=" * 80)
    print("TEST 4: Full Price Comparison")
    print("=" * 80)
    
    if not old_docx_path or not new_docx_path:
        print("⚠️  SKIPPED: No document paths provided")
        print("   Usage: python test_price_detection.py old.docx new.docx")
        return True
    
    if not os.path.exists(old_docx_path):
        print(f"❌ FAIL: Old document not found: {old_docx_path}")
        return False
    
    if not os.path.exists(new_docx_path):
        print(f"❌ FAIL: New document not found: {new_docx_path}")
        return False
    
    print(f"Parsing old document: {old_docx_path}")
    parser = PAPLParser()
    old_data = parser.parse(old_docx_path)
    print(f"  ✅ Found {len(old_data['raw_tables'])} tables")
    
    print(f"Parsing new document: {new_docx_path}")
    new_data = parser.parse(new_docx_path)
    print(f"  ✅ Found {len(new_data['raw_tables'])} tables")
    
    print("\nComparing documents...")
    comparer = SemanticComparer()
    results = comparer.compare_with_price_detection(old_data, new_data)
    
    # Display price changes
    price_changes = results.get('price_changes', {}).get('changes', [])
    
    print(f"\n{'=' * 80}")
    print(f"PRICE CHANGES DETECTED: {len(price_changes)}")
    print(f"{'=' * 80}")
    
    if price_changes:
        print("\nTop 10 price changes:")
        for i, change in enumerate(price_changes[:10], 1):
            item = change.get('item_number', 'Unknown')
            desc = change.get('item_description', '')[:40]
            old = change['old_price']
            new = change['new_price']
            diff = change['difference']
            pct = change['percent_change']
            
            print(f"\n{i}. Item {item}: {desc}")
            print(f"   ${old:.2f} → ${new:.2f}")
            print(f"   Change: ${diff:+.2f} ({pct:+.1f}%)")
            print(f"   Location: Table {change['old_location']['table']}, Row {change['old_location']['row']}")
        
        if len(price_changes) > 10:
            print(f"\n... and {len(price_changes) - 10} more price changes")
        
        # Summary statistics
        increases = sum(1 for c in price_changes if c['difference'] > 0)
        decreases = sum(1 for c in price_changes if c['difference'] < 0)
        avg_change = sum(c['difference'] for c in price_changes) / len(price_changes)
        
        print(f"\n{'=' * 80}")
        print("SUMMARY")
        print(f"{'=' * 80}")
        print(f"Total price changes: {len(price_changes)}")
        print(f"Price increases: {increases}")
        print(f"Price decreases: {decreases}")
        print(f"Average change: ${avg_change:+.2f}")
        
        print("\n✅ SUCCESS: Price changes detected!")
        print("\nCompare this to Andrew's test:")
        print("  - Andrew's test: 0 prices detected (WRONG)")
        print(f"  - This test: {len(price_changes)} prices detected (CORRECT!)")
    else:
        print("\n⚠️  WARNING: No price changes detected")
        print("   If you know there are price changes in these documents,")
        print("   the fix may not be working correctly.")
    
    return True


def main():
    """Run all tests"""
    print("\n" + "=" * 80)
    print("PRICE DETECTION FIX - TEST SUITE")
    print("=" * 80)
    
    # Get document paths from command line if provided
    old_docx = sys.argv[1] if len(sys.argv) > 1 else None
    new_docx = sys.argv[2] if len(sys.argv) > 2 else None
    
    # Run unit tests
    test1 = test_price_extraction()
    test2 = test_item_number_extraction()
    test3 = test_pricing_table_detection()
    
    # Run integration test if documents provided
    test4 = test_price_comparison(old_docx, new_docx)
    
    # Summary
    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    print(f"Price extraction: {'✅ PASS' if test1 else '❌ FAIL'}")
    print(f"Item number extraction: {'✅ PASS' if test2 else '❌ FAIL'}")
    print(f"Pricing table detection: {'✅ PASS' if test3 else '❌ FAIL'}")
    print(f"Full comparison: {'✅ PASS' if test4 else '❌ FAIL'}")
    
    all_passed = test1 and test2 and test3 and test4
    
    if all_passed:
        print("\n🎉 ALL TESTS PASSED!")
        print("\nNext steps:")
        print("1. Test with Andrew's documents (Oct 2024 vs July 2025 PAPL)")
        print("2. Verify price changes are detected")
        print("3. Deploy to Render if working correctly")
    else:
        print("\n❌ SOME TESTS FAILED")
        print("Fix the issues before deploying")
    
    return 0 if all_passed else 1


if __name__ == '__main__':
    sys.exit(main())
