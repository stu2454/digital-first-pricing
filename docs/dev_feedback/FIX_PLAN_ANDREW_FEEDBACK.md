# Fix Plan - Andrew's Feedback

**Priority:** CRITICAL  
**Timeline:** 2-4 weeks  
**Goal:** Make price detection actually work

---

## 🎯 The Core Problem

**What Andrew Found:**
- Tested Oct 2024 PAPL vs July 2025 PAPL
- Tool said: "0 prices changed, 6 prices added"
- Reality: "a bunch of prices did change"

**Why This Matters:**
Price detection is the #1 use case. If this doesn't work, the tool is useless.

---

## 📋 Issues Ranked by Impact

### 🔴 Critical (Fix First)

| # | Issue | Impact | Effort |
|---|-------|--------|--------|
| 1 | Price changes not detected | SHOWSTOPPER | Medium |
| 2 | Structure changes break matching | HIGH | High |
| 6 | Section renames → false add/delete | HIGH | Medium |

### 🟡 Important (Fix Second)

| # | Issue | Impact | Effort |
| 3 | False positive pricing tables | MEDIUM | Low |
| 5 | Section classification unclear | MEDIUM | Medium |

### 🔵 Polish (Fix Third)

| # | Issue | Impact | Effort |
| 4 | Poor links to source | MEDIUM | Medium |
| 7 | Random result ordering | LOW | Low |

---

## 🚀 Phase 1: Make It Work (Week 1-2)

### Fix #1: Price Detection
**File:** `shared/semantic_comparer.py`

**Problem:** Treating "$50" and "$55" as "similar text"

**Solution:** Extract and compare prices numerically

```python
import re

def extract_price(text):
    """Extract dollar amount from text"""
    match = re.search(r'\$(\d+(?:\.\d{2})?)', text)
    return float(match.group(1)) if match else None

def compare_prices(old_cell, new_cell):
    """Compare prices numerically, not semantically"""
    old_price = extract_price(old_cell.text)
    new_price = extract_price(new_cell.text)
    
    if old_price and new_price:
        if old_price != new_price:
            return {
                'type': 'price_changed',
                'old_price': f"${old_price:.2f}",
                'new_price': f"${new_price:.2f}",
                'difference': new_price - old_price,
                'percent_change': ((new_price - old_price) / old_price) * 100
            }
    return None
```

**Test:** Oct 2024 vs July 2025 PAPL should show ALL price changes

---

### Fix #2: Item Number Matching
**File:** `shared/semantic_comparer.py`

**Problem:** Position-based matching breaks when table structure changes

**Solution:** Match by item number, not position

```python
def match_tables_by_item_number(old_table, new_table):
    """Match table rows by item number, handle structure changes"""
    
    # Extract item numbers and prices
    old_items = {}
    for row in old_table.rows[1:]:  # Skip header
        item_num = extract_item_number(row)
        if item_num:
            old_items[item_num] = extract_price_from_row(row)
    
    new_items = {}
    for row in new_table.rows[1:]:
        item_num = extract_item_number(row)
        if item_num:
            new_items[item_num] = extract_price_from_row(row)
    
    # Compare prices for matching items
    changes = []
    for item_num in old_items:
        if item_num in new_items:
            if old_items[item_num] != new_items[item_num]:
                changes.append({
                    'item_number': item_num,
                    'change_type': 'price_changed',
                    'old_price': old_items[item_num],
                    'new_price': new_items[item_num]
                })
    
    return changes
```

**Test:** Therapy supports (state → national pricing) should show price changes

---

### Fix #6: Section Title Fuzzy Matching
**File:** `shared/semantic_comparer.py`

**Problem:** "Therapy Support" → "Therapy Supports" treated as delete + add

**Solution:** Fuzzy match section titles

```python
from fuzzywuzzy import fuzz

def match_sections_fuzzy(old_sections, new_sections):
    """Match sections even if title slightly changed"""
    
    matched_pairs = []
    unmatched_old = []
    unmatched_new = list(new_sections)
    
    for old_sec in old_sections:
        best_match = None
        best_score = 0
        
        for new_sec in unmatched_new:
            # Title similarity
            title_sim = fuzz.ratio(old_sec.title, new_sec.title)
            
            # Content similarity (first 200 chars)
            content_sim = fuzz.ratio(
                old_sec.text[:200],
                new_sec.text[:200]
            )
            
            # Weighted score
            score = (title_sim * 0.3) + (content_sim * 0.7)
            
            if score > best_score:
                best_score = score
                best_match = new_sec
        
        # If good match found, it's a modification
        if best_score > 85:
            matched_pairs.append((old_sec, best_match))
            unmatched_new.remove(best_match)
        else:
            unmatched_old.append(old_sec)
    
    return matched_pairs, unmatched_old, unmatched_new
```

**Test:** "Therapy Support" → "Therapy Supports" should show as title change, not 19 add + 19 delete

---

## 🔧 Phase 2: Improve Quality (Week 3-4)

### Fix #3: Better Pricing Table Detection

Add confidence scoring:

```python
def is_pricing_table(table, context):
    """Determine if table is actually pricing table"""
    score = 0
    
    # Check headers
    headers = [cell.text.lower() for cell in table.rows[0].cells]
    if any(word in ' '.join(headers) for word in ['price', 'rate', 'amount', 'cost']):
        score += 40
    
    # Check for item numbers
    if has_item_number_column(table):
        score += 30
    
    # Check context
    if 'pricing' in context.section_title.lower():
        score += 20
    
    # Check for multiple price values
    if count_price_cells(table) > 3:
        score += 10
    
    return score >= 60, score
```

---

### Fix #5: Better Section Classification

Show hierarchy:

```
Section Added: "Provider Travel" (Section 5.3)
  ├─ Rule Added: "Travel claims must include..."
  ├─ Rule Added: "Maximum travel distance is..."
  └─ Guidance Added: "Providers should note..."
```

---

## ✨ Phase 3: Polish (Week 5-6)

### Fix #4: Better Source Links

Add side-by-side context:

```
OLD (Oct 2024):                      NEW (July 2025):
─────────────────────────────────   ─────────────────────────────────
Item 01_001                         Item 01_001
Standard Consultation               Standard Consultation
Price: $50.00                       Price: $55.00
                                    
Table 5, Row 3, Page ~47            Table 5, Row 3, Page ~52
```

---

### Fix #7: Logical Result Ordering

Sort by document order:

```python
changes.sort(key=lambda c: (
    c.table_number,
    c.row_number,
    c.paragraph_number
))
```

---

## 🧪 Testing Checklist

After each fix, test with:

- [ ] Oct 2024 PAPL vs July 2025 PAPL (Andrew's test case)
- [ ] Specific table Andrew mentioned (undetected price changes)
- [ ] Therapy supports section (structure change)
- [ ] "Therapy Support" rename case
- [ ] Tables with dollar signs but not pricing

---

## 📊 Success Criteria

**Before Fixes:**
- Price detection: 0% ❌
- Structure handling: Broken ❌
- Section matching: Poor ❌

**After Fixes:**
- Price detection: 100% ✅
- Structure handling: Works ✅
- Section matching: >90% accurate ✅

---

## 💬 Next Steps

### This Week:
1. Get test documents from Andrew (Oct 2024, July 2025 PAPLs)
2. Implement Fix #1 (price detection)
3. Test with Andrew's case
4. Deploy to dev environment

### Week 2:
1. Implement Fix #2 (item number matching)
2. Implement Fix #6 (section fuzzy matching)
3. Test all three fixes together
4. Get Andrew to validate

### Week 3-4:
1. Implement remaining fixes
2. Full regression testing
3. Update documentation
4. Deploy to production

---

## 🎯 Quick Win

**Start with Fix #1 only** - price detection is the most critical and can be done quickly:

1. Add `extract_price()` function
2. Add `compare_prices()` function
3. Call before semantic comparison
4. Test with Oct 2024 vs July 2025

**Timeline:** 2-3 days  
**Impact:** Immediate improvement to core functionality

---

## 📞 Communication

### To Andrew:
> Thanks for the detailed feedback! I've prioritized the issues:
> 
> **Fixing this week:**
> - Price detection (the critical one)
> 
> **Fixing next week:**
> - Item number matching (for structure changes)
> - Section title fuzzy matching
> 
> Can you share the test PAPLs so I can reproduce the exact issues? I'll have fixes ready for re-testing in ~2 weeks.

### To Stakeholders:
> Expert testing revealed critical issues with price detection. Pausing broader rollout until fixes complete (~2 weeks). This is exactly why we do beta testing!

---

## 🚨 Remember

**DO NOT** roll out to wider audience until price detection works correctly. This is the tool's core value - if it's broken, the tool is useless.

**Priority order matters:**
1. Fix price detection (Week 1)
2. Fix structure matching (Week 2)  
3. Fix section matching (Week 2)
4. Everything else (Week 3-4)

---

*Start with Fix #1 today. Test with Andrew's documents. Iterate quickly.* 🚀

---

**Files to Modify:**
- `shared/semantic_comparer.py` (all fixes)
- `shared/papl_parser.py` (extraction helpers)
- `apps/02-papl-comparison/app.py` (display improvements)

**Expected LOC:** ~200-300 lines of new code

**Current Status:** 🔴 Tool not production-ready  
**Target Status:** ✅ Tool works correctly for price detection
