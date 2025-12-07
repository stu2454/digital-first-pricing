# Expert Feedback Analysis - Andrew's PAPL Comparison Issues

**Date:** December 2024  
**Reviewer:** Andrew (PAPL Expert)  
**Test:** Oct 2024 PAPL vs. July 2025 PAPL  
**Status:** 🔴 Critical Issues Identified

---

## 📊 Executive Summary

Andrew tested the PAPL comparison tool with real-world documents and identified **7 major issues** that need addressing. The most critical: **price changes are not being detected**, even in tables with no format changes. This undermines the core value proposition of the tool.

**Key Finding:** The tool reported "0 prices changed, 6 prices added" when in reality **many prices did change**.

---

## 🚨 Critical Issues (Priority Order)

### 🔴 **ISSUE 1: Price Changes Not Detected**
**Priority:** CRITICAL - Core functionality broken  
**Impact:** Tool's primary purpose is to detect price changes

**Problem:**
- Comparing Oct 2024 → July 2025 PAPL
- Tool reported: "0 prices changed"
- Reality: "a bunch of prices did change"
- Even tables with **only price changes** (no format changes) weren't flagged

**Example:**
> "this table between the versions has no changes other than prices, but did not get flagged as price change"

**Root Cause Hypothesis:**
1. Semantic comparison treating price as "similar enough" content
2. Price comparison logic not specifically looking for dollar amount changes
3. Fuzzy matching threshold too lenient for numerical values
4. Not comparing numbers numerically (treating "$50" and "$55" as similar text)

**Fix Required:**
- Add specific price detection logic
- Extract dollar amounts with regex: `\$\d+(?:\.\d{2})?`
- Compare prices numerically, not semantically
- Flag ANY difference in dollar amounts as "Price Changed"
- Even 1 cent difference should be flagged

**Code Location:**
- `papl_parser.py` - Extract prices from tables
- `semantic_comparer.py` - Add price-specific comparison

---

### 🟡 **ISSUE 2: Table Structure Changes Breaking Price Detection**
**Priority:** HIGH - Known scenario (state → national pricing)

**Problem:**
- Therapy pricing tables changed structure
- Old: Multiple state columns with different prices per state
- New: Single national price column
- Tool didn't recognize this as price changes

**Andrew's Suggestion:**
> "maybe it can try looking to check against the item numbers to flag 'Possible price change' or similar"

**Solution Approach:**
1. **Extract Item Numbers** from both versions
2. **Match by Item Number** (ignore position)
3. **Compare prices** for same item number
4. **Flag as "Possible Price Change"** if:
   - Structure changed AND
   - Item has price in both versions AND
   - Prices differ

**Implementation:**
```python
# Pseudo-code
def compare_pricing_by_item_number(old_table, new_table):
    old_items = extract_items_with_prices(old_table)
    new_items = extract_items_with_prices(new_table)
    
    changes = []
    for item_num in old_items.keys():
        if item_num in new_items:
            old_price = extract_price(old_items[item_num])
            new_price = extract_price(new_items[item_num])
            
            if old_price != new_price:
                changes.append({
                    'item_number': item_num,
                    'old_price': old_price,
                    'new_price': new_price,
                    'change_type': 'Price Changed' if structure_same else 'Possible Price Change'
                })
    
    return changes
```

**Benefits:**
- Handles structural changes
- Matches by logical key (item number) not position
- More robust to table reformatting

---

### 🟡 **ISSUE 3: False Positive Price Changes**
**Priority:** MEDIUM - Quality/accuracy issue

**Problem:**
> "the one new table it did flag as price change was not a price change - but since it has dollar figures, I get why it thinks it is a new pricing table"

**Root Cause:**
- Tool sees dollar signs/amounts → assumes pricing table
- But not all dollar figures are prices (could be examples, calculations, etc.)

**Solution:**
1. **Check table context:**
   - Is it in a pricing section?
   - Does it have column headers like "Price", "Rate", "Amount"?
   - Does it have item numbers?
   
2. **Heuristics for pricing tables:**
   - Multiple rows with consistent dollar amounts
   - Column structure: Item | Description | Price
   - Located in specific PAPL sections
   
3. **Classification confidence:**
   - High confidence: Clear pricing structure
   - Medium: Has prices but unclear context
   - Low: Dollar figures but likely not pricing

**Implementation:**
```python
def is_pricing_table(table, context):
    confidence = 0
    
    # Check headers
    if has_price_headers(table):
        confidence += 40
    
    # Check for item numbers
    if has_item_numbers(table):
        confidence += 30
    
    # Check section context
    if context.section_title.contains('pricing', 'price', 'rate'):
        confidence += 20
    
    # Check for consistent dollar format
    if has_consistent_price_column(table):
        confidence += 10
    
    return confidence >= 60  # Threshold
```

---

### 🟠 **ISSUE 4: Poor Direct Links to Source Documents**
**Priority:** HIGH - User experience critical

**Problem:**
> "I also want it to do better at providing direct links back to changes in the original word documents. I need a better way to track changes"

**Current State:**
- Tool shows: "Table 5, Row 3"
- But finding this in a 104-page document is hard
- No way to jump directly to the change in Word

**Challenge:**
- Word documents don't have anchor links like HTML
- Can't create clickable links to specific paragraphs/tables

**Possible Solutions:**

**Option 1: Page Numbers**
```
Change found at:
- Table 5, Row 3
- Page: 47 (approximate)
- Paragraph: 245
```

**Option 2: Searchable Context**
```
Change found:
"...surrounding text context..."
Search in document for: "unique phrase from that section"
```

**Option 3: Side-by-Side Snippets**
```
OLD (Oct 2024):                  NEW (July 2025):
[actual text from table]         [actual text from table]
Table 5, Row 3, Page ~47         Table 5, Row 3, Page ~52
```

**Option 4: Export Comparison Document**
- Generate Word doc with tracked changes
- Highlight each change with comment
- Links back to line numbers

**Recommendation:**
- Implement Option 3 (side-by-side) immediately
- Add Option 1 (page numbers) if possible
- Option 4 for advanced users

---

### 🟠 **ISSUE 5: Section Classification Problems**
**Priority:** MEDIUM - Classification accuracy

**Problem 1: "Section add of 0"**
> "This one Section add of 0 I think should be more - but it has put the new bit in the Rule Added?"

**Problem 2: New rules in new sections**
> "Not sure how it should treat it where new rules texts are added in new sections"

**Root Cause:**
- Tool classifies content by type (rule/guidance/pricing)
- When new section is added WITH new rules, it's unclear:
  - Is it a new section? (structural change)
  - Is it a new rule? (content change)
  - Or both?

**Solution:**
1. **Hierarchical Change Tracking:**
   ```
   Section Added: "Provider Travel" (Section 5.3)
   ├─ Rule Added: "Travel claims must include..."
   ├─ Rule Added: "Maximum travel distance is..."
   └─ Guidance Added: "Providers should note..."
   ```

2. **Classification Precedence:**
   - If new section contains new rules → Show both
   - Section change is structural
   - Rule/guidance changes are content
   - Both are important, show both

3. **Better Labeling:**
   ```
   Instead of: "Rule Added (1)"
   Show: "New Rule in New Section: Provider Travel (Section 5.3)"
   ```

---

### 🟡 **ISSUE 6: Section Title Changes Causing False Additions/Deletions**
**Priority:** HIGH - Major accuracy issue

**Problem:**
> "we've added and removed 19 paragraphs for Therapy Supports, I think because the title of the section changed, rather than modified it"

**Root Cause:**
- Section matching by exact title
- When title changes: "Therapy Support" → "Therapy Supports"
- Tool thinks:
  - Old section deleted (19 paragraphs removed)
  - New section added (19 paragraphs added)
- Reality: Section renamed, content same

**Solution:**
1. **Fuzzy Section Matching:**
   ```python
   def match_sections(old_sections, new_sections):
       # First: Try exact match
       # Second: Try fuzzy match (>90% similar)
       # Third: Try content-based match
       
       from fuzzywuzzy import fuzz
       
       for old_sec in old_sections:
           best_match = None
           best_score = 0
           
           for new_sec in new_sections:
               # Title similarity
               title_score = fuzz.ratio(old_sec.title, new_sec.title)
               
               # Content similarity (first 200 chars)
               content_score = fuzz.ratio(
                   old_sec.content[:200], 
                   new_sec.content[:200]
               )
               
               # Combined score
               score = (title_score * 0.3 + content_score * 0.7)
               
               if score > best_score and score > 85:
                   best_match = new_sec
                   best_score = score
           
           if best_match:
               # This is a modification, not add/delete
               compare_sections(old_sec, best_match)
   ```

2. **Change Classification:**
   ```
   Instead of:
   - Section Removed: "Therapy Support"
   - Section Added: "Therapy Supports"
   
   Show:
   - Section Title Changed: "Therapy Support" → "Therapy Supports"
   - Content: No changes
   ```

---

### 🔵 **ISSUE 7: Poor Result Ordering**
**Priority:** LOW - User experience improvement

**Problem:**
> "Row 3, 4, 2, 6, 1, 5 from same table is probably not the best ordering to flag changes"

**Current Behavior:**
- Changes from same table displayed in random order
- Confusing to verify against source document

**Solution:**
1. **Sort by logical order:**
   ```python
   def sort_changes(changes):
       return sorted(changes, key=lambda c: (
           c.table_number,      # Table 1, 2, 3...
           c.section_number,    # Section 1.1, 1.2...
           c.row_number,        # Row 1, 2, 3...
           c.paragraph_number   # Paragraph 1, 2, 3...
       ))
   ```

2. **Group by location:**
   ```
   Table 5 Changes:
   ├─ Row 1: Price changed $50 → $55
   ├─ Row 2: Description modified
   ├─ Row 3: Price changed $100 → $110
   └─ Row 5: Item added
   ```

3. **Visual separation:**
   - Group changes from same table
   - Clear dividers between tables
   - Maintain document order

---

## 🎯 Recommended Fix Priority

### Phase 1: Critical Fixes (Week 1-2)
**Goal:** Make tool actually work for its primary purpose

1. ✅ **Fix price detection** (Issue #1)
   - Add numerical price comparison
   - Extract dollar amounts specifically
   - Flag all price changes

2. ✅ **Item number-based matching** (Issue #2)
   - Match tables by item numbers
   - Handle structural changes
   - Flag "Possible Price Change"

3. ✅ **Fix section title matching** (Issue #6)
   - Fuzzy matching for section titles
   - Content-based matching
   - Reduce false add/delete

### Phase 2: Quality Improvements (Week 3-4)
**Goal:** Improve accuracy and reduce false positives

4. ✅ **Better pricing table detection** (Issue #3)
   - Heuristics for true pricing tables
   - Confidence scoring
   - Reduce false positives

5. ✅ **Better section classification** (Issue #5)
   - Hierarchical change display
   - Show structure + content changes
   - Better labeling

### Phase 3: UX Improvements (Week 5-6)
**Goal:** Make tool easier to use and verify

6. ✅ **Improve source document links** (Issue #4)
   - Side-by-side context display
   - Page number estimates
   - Better verification workflow

7. ✅ **Fix result ordering** (Issue #7)
   - Logical sort order
   - Grouped by location
   - Visual hierarchy

---

## 💻 Technical Implementation Notes

### Files to Modify:

**1. `shared/papl_parser.py`**
```python
# Add methods:
- extract_item_numbers(table)
- extract_prices(table)  
- is_pricing_table(table, context)
- get_approximate_page_number(element)
```

**2. `shared/semantic_comparer.py`**
```python
# Add/modify methods:
- compare_prices_numerically(old_price, new_price)
- match_tables_by_item_number(old_tables, new_tables)
- match_sections_fuzzy(old_sections, new_sections)
- classify_change_with_confidence(change)
- sort_changes_logically(changes)
```

**3. `apps/02-papl-comparison/app.py`**
```python
# Display improvements:
- Group changes by location
- Show side-by-side context
- Add confidence indicators
- Better visual hierarchy
```

---

## 🧪 Testing Strategy

### Test Cases Needed:

**Test 1: Price Changes**
- Input: Oct 2024 PAPL vs July 2025 PAPL
- Expected: All price changes detected
- Current: FAIL (0 detected, many existed)

**Test 2: Structure Changes**
- Input: State-based pricing → National pricing
- Expected: Detect price changes via item number matching
- Current: FAIL (not detected)

**Test 3: Section Renames**
- Input: "Therapy Support" → "Therapy Supports"
- Expected: Section title change, not add/delete
- Current: FAIL (19 false add, 19 false delete)

**Test 4: Non-Pricing Tables**
- Input: Table with dollar figures but not pricing
- Expected: Not classified as pricing table
- Current: FAIL (false positive)

**Test 5: Result Ordering**
- Input: Any comparison with multiple changes
- Expected: Changes ordered by table, then row
- Current: FAIL (random order)

---

## 📊 Success Metrics

**Before (Current State):**
- Price detection: 0% (0 of many detected)
- False positives: ~10% (1 false pricing table)
- Section accuracy: Poor (19 false add/delete)
- Result ordering: Random

**After (Target State):**
- Price detection: 100% (all price changes caught)
- False positives: <5%
- Section accuracy: >90% correct classification
- Result ordering: 100% logical

---

## 💬 Response to Andrew

**Message to send:**

> Hi Andrew,
> 
> Thank you for the detailed feedback - this is exactly what we need! I've analyzed all 7 issues you identified:
> 
> **Critical Issues (fixing first):**
> 1. Price detection broken - adding numerical comparison
> 2. Item number matching needed - for structure changes
> 3. Section title matching - fixing "Therapy Support/Supports" issue
> 
> **Next Priority:**
> 4. Better pricing table detection - reduce false positives
> 5. Section classification improvements
> 
> **User Experience:**
> 6. Better source document links - adding side-by-side context
> 7. Result ordering - logical table/row order
> 
> I'm prioritizing price detection (#1) first since that's the tool's core value. Would you be willing to test again after fixes are implemented in ~2 weeks?
> 
> Also - **please use the Feedback tab in the tool** to submit any additional issues! It saves directly to S3 for easy tracking.
> 
> Thanks again,
> Stuart

---

## 📋 Action Items for Stuart

### Immediate:
- [ ] Acknowledge Andrew's feedback (use message above)
- [ ] Ask if he can provide the test documents (Oct 2024, July 2025 PAPLs)
- [ ] Ask for specific examples (which tables had undetected price changes)
- [ ] Schedule follow-up testing session

### Development:
- [ ] Create new branch: `fix/andrew-feedback`
- [ ] Implement Phase 1 fixes (price detection)
- [ ] Write test cases with Andrew's examples
- [ ] Deploy to dev environment for Andrew to test
- [ ] Iterate based on his validation

### Communication:
- [ ] Document known issues in About tab
- [ ] Add "Beta" warning until fixes complete
- [ ] Share fix timeline with stakeholders
- [ ] Regular updates to Andrew on progress

---

## 🎓 Key Learnings

### What Went Wrong:
1. **Semantic comparison too lenient** - treating "$50" and "$55" as "similar"
2. **Position-based matching** - breaks when structure changes
3. **Exact string matching** - too brittle for section titles
4. **Assumed table context** - not all dollar signs = pricing
5. **No domain expertise in testing** - needed PAPL expert earlier

### What Went Right:
1. **Beta testing with expert** - caught critical issues early
2. **Specific, actionable feedback** - Andrew gave great examples
3. **Fast feedback loop** - can iterate quickly
4. **S3 feedback system** - will collect more structured feedback going forward

### Going Forward:
1. **Domain expert testing essential** - before broader rollout
2. **Numerical comparison for prices** - don't use semantic matching
3. **Logical key matching** - use item numbers, not positions
4. **Confidence scoring** - acknowledge uncertainty
5. **Iterative refinement** - expect multiple rounds of fixes

---

## 📈 Impact Assessment

**If Not Fixed:**
- Tool unusable for actual PAPL comparisons
- Loss of stakeholder confidence
- Cannot proceed with pilot evaluation
- Core value proposition undermined

**If Fixed:**
- Tool becomes genuinely useful
- Can proceed with pilot
- Build stakeholder confidence
- Demonstrate clear value vs. manual comparison

**Priority:** CRITICAL - Do not deploy widely until price detection works correctly.

---

## 🆘 Questions for Andrew (Follow-up)

1. Can you share the exact documents you tested? (Oct 2024 & July 2025 PAPLs)
2. Which specific tables had undetected price changes? (screenshots helpful)
3. What's the most important fix for your use case? (price detection? structure changes? links?)
4. Would you be willing to test again in 2 weeks after fixes?
5. Are there other test scenarios you'd recommend?
6. What's the minimum accuracy needed for you to find this useful?

---

**This feedback is gold - it's exactly what's needed to make the tool production-ready.** 🎯

---

*Created: December 2024*  
*Based on: Andrew's expert testing of Oct 2024 vs July 2025 PAPL*  
*Status: Critical issues identified, fixes prioritized*  
*Next: Implement Phase 1 fixes (2 weeks)*
