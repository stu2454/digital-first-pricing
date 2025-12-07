"""
Semantic Comparer for PAPL Documents
Compares two parsed PAPL documents and identifies meaningful changes

Enhanced with numerical price detection to catch price changes that
semantic text comparison might miss
"""

from typing import Dict, List, Any, Optional, Tuple
from fuzzywuzzy import fuzz
import json


class SemanticComparer:
    """
    Compare PAPL documents semantically
    
    Identifies:
    - Price changes (numerical comparison)
    - Business rule changes
    - Guidance changes
    - Structural changes (sections added/removed)
    - Table changes
    """
    
    def __init__(self, similarity_threshold: int = 85):
        """
        Initialize semantic comparer
        
        Args:
            similarity_threshold: Minimum similarity score (0-100) to consider
                                 content as "similar" rather than "changed"
        """
        self.similarity_threshold = similarity_threshold
    
    def compare(self, old_doc_data: Dict[str, Any], new_doc_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Compare two parsed PAPL documents
        
        NOW ENHANCED: Detects price changes explicitly before semantic comparison
        
        Args:
            old_doc_data: Parsed data from old PAPL (from PAPLParser.parse())
            new_doc_data: Parsed data from new PAPL (from PAPLParser.parse())
            
        Returns:
            Dict with categorized changes including:
            - price_changes: Numerical price comparisons
            - business_rule_changes: Rule modifications
            - guidance_changes: Guidance text changes
            - structural_changes: Sections added/removed
            - table_changes: Table structure changes
            - summary: Overall statistics
        """
        # Use the new price-aware comparison
        return self.compare_with_price_detection(old_doc_data, new_doc_data)
    
    def compare_with_price_detection(self, old_doc_data: Dict[str, Any], new_doc_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Compare documents with explicit price change detection
        
        This method runs numerical price comparison BEFORE semantic text comparison
        to ensure we don't miss price changes due to fuzzy matching
        
        Args:
            old_doc_data: Parsed data from old PAPL
            new_doc_data: Parsed data from new PAPL
            
        Returns:
            Dict with all changes including explicit price changes
        """
        # Import parser for price extraction
        from papl_parser import PAPLParser
        parser = PAPLParser()
        
        # STEP 1: Detect price changes explicitly (numerical comparison)
        price_changes = self._compare_all_prices(
            old_doc_data.get('raw_tables', []),
            new_doc_data.get('raw_tables', []),
            parser
        )
        
        # STEP 2: Do semantic comparison for everything else
        semantic_results = self._compare_semantic(old_doc_data, new_doc_data)
        
        # STEP 3: Merge results, prioritizing explicit price changes
        result = semantic_results.copy()
        
        # Add price changes as separate section
        result['price_changes'] = {
            'count': len(price_changes),
            'changes': price_changes,
            'summary': self._summarize_price_changes(price_changes)
        }
        
        # Update overall summary counts
        if 'summary' not in result:
            result['summary'] = {}
        
        result['summary']['total_price_changes'] = len(price_changes)
        result['summary']['price_increases'] = sum(1 for c in price_changes if c['difference'] > 0)
        result['summary']['price_decreases'] = sum(1 for c in price_changes if c['difference'] < 0)
        
        if price_changes:
            avg_change = sum(c['difference'] for c in price_changes) / len(price_changes)
            result['summary']['average_price_change'] = round(avg_change, 2)
        
        return result
    
    def _compare_all_prices(self, old_tables: List[Dict], new_tables: List[Dict], parser) -> List[Dict[str, Any]]:
        """
        Compare prices across all tables in both documents
        
        ENHANCED: Now handles table position changes!
        - First tries position-based matching (table 0 vs 0, 1 vs 1, etc.)
        - Then tries to match remaining pricing tables by header similarity
        - This handles cases where pricing tables moved positions between versions
        
        Args:
            old_tables: Tables from old document
            new_tables: Tables from new document
            parser: PAPLParser instance for extraction methods
            
        Returns:
            List of all price changes found
        """
        all_changes = []
        
        # Track which tables we've already compared
        old_compared = set()
        new_compared = set()
        
        # STRATEGY 1: Match tables by position (original behavior)
        # This handles tables that haven't moved
        max_tables = min(len(old_tables), len(new_tables))
        
        for i in range(max_tables):
            old_table = old_tables[i]
            new_table = new_tables[i]
            
            # Check if both are pricing tables
            old_is_pricing, old_confidence = parser._is_pricing_table(old_table)
            new_is_pricing, new_confidence = parser._is_pricing_table(new_table)
            
            # Only compare if both are pricing tables
            if old_is_pricing and new_is_pricing:
                changes = parser._compare_table_prices(old_table, new_table)
                all_changes.extend(changes)
                old_compared.add(i)
                new_compared.add(i)
        
        # STRATEGY 2: Match remaining pricing tables by header similarity
        # This handles tables that moved positions
        
        # Find remaining pricing tables in OLD document
        old_pricing_tables = []
        for i, table in enumerate(old_tables):
            if i not in old_compared:
                is_pricing, confidence = parser._is_pricing_table(table)
                if is_pricing:
                    old_pricing_tables.append((i, table, confidence))
        
        # Find remaining pricing tables in NEW document
        new_pricing_tables = []
        for i, table in enumerate(new_tables):
            if i not in new_compared:
                is_pricing, confidence = parser._is_pricing_table(table)
                if is_pricing:
                    new_pricing_tables.append((i, table, confidence))
        
        # Try to match remaining pricing tables by header similarity
        for old_idx, old_table, old_conf in old_pricing_tables:
            old_headers = self._get_table_headers(old_table)
            best_match_idx = None
            best_similarity = 0
            
            for new_idx, new_table, new_conf in new_pricing_tables:
                if new_idx in new_compared:
                    continue
                
                new_headers = self._get_table_headers(new_table)
                
                # Calculate header similarity
                similarity = self._calculate_header_similarity(old_headers, new_headers)
                
                if similarity > best_similarity and similarity > 0.5:  # At least 50% similar
                    best_similarity = similarity
                    best_match_idx = new_idx
            
            # If we found a good match, compare these tables
            if best_match_idx is not None:
                new_table = new_tables[best_match_idx]
                changes = parser._compare_table_prices(old_table, new_table)
                all_changes.extend(changes)
                new_compared.add(best_match_idx)
        
        # Remove duplicates based on item number AND column
        # Each item can have multiple prices (National, Remote, Very Remote)
        seen_items = set()
        unique_changes = []
        
        for change in all_changes:
            item_num = change.get('item_number')
            col_idx = change.get('new_location', {}).get('col')
            
            # Create unique key from item_number + column
            if item_num and col_idx is not None:
                item_key = (item_num, col_idx)
            elif item_num:
                # Fallback if no column info
                item_key = (item_num, 'unknown')
            else:
                # No item number - use location as key
                item_key = (change.get('new_location', {}).get('table'), 
                           change.get('new_location', {}).get('row'),
                           change.get('new_location', {}).get('col'))
            
            if item_key not in seen_items:
                seen_items.add(item_key)
                unique_changes.append(change)
        
        return unique_changes
    
    def _get_table_headers(self, table: Dict) -> List[str]:
        """Extract headers from a table"""
        data = table.get('data', [])
        if not data or len(data) == 0:
            return []
        return [str(h).lower().strip() for h in data[0]]
    
    def _calculate_header_similarity(self, headers1: List[str], headers2: List[str]) -> float:
        """Calculate similarity between two sets of headers"""
        if not headers1 or not headers2:
            return 0.0
        
        # Count matching headers
        matches = 0
        for h1 in headers1:
            for h2 in headers2:
                # Check if headers are similar (contains same key words)
                h1_words = set(h1.split())
                h2_words = set(h2.split())
                if h1_words & h2_words:  # If there's any overlap
                    matches += 1
                    break
        
        # Similarity is proportion of matching headers
        max_headers = max(len(headers1), len(headers2))
        return matches / max_headers if max_headers > 0 else 0.0
    
    
    def _summarize_price_changes(self, price_changes: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Create summary statistics for price changes
        
        Args:
            price_changes: List of price change dictionaries
            
        Returns:
            Summary statistics dictionary
        """
        if not price_changes:
            return {
                'total_changes': 0,
                'increases': 0,
                'decreases': 0,
                'unchanged': 0
            }
        
        increases = [c for c in price_changes if c['difference'] > 0]
        decreases = [c for c in price_changes if c['difference'] < 0]
        
        summary = {
            'total_changes': len(price_changes),
            'increases': len(increases),
            'decreases': len(decreases),
            'average_change': round(sum(c['difference'] for c in price_changes) / len(price_changes), 2),
            'largest_increase': max((c['difference'] for c in increases), default=0),
            'largest_decrease': min((c['difference'] for c in decreases), default=0),
            'total_increase_amount': round(sum(c['difference'] for c in increases), 2),
            'total_decrease_amount': round(sum(c['difference'] for c in decreases), 2)
        }
        
        return summary
    
    def _is_price_change(self, old_text: str, new_text: str) -> Optional[Dict[str, Any]]:
        """
        Check if text change is specifically a price change
        
        Args:
            old_text: Old text
            new_text: New text
            
        Returns:
            Price change dict if it's a price change, None otherwise
        """
        from papl_parser import PAPLParser
        parser = PAPLParser()
        
        old_price = parser._extract_price(old_text)
        new_price = parser._extract_price(new_text)
        
        if old_price and new_price and old_price != new_price:
            difference = new_price - old_price
            percent_change = (difference / old_price) * 100 if old_price > 0 else 0
            
            return {
                'old_price': old_price,
                'new_price': new_price,
                'difference': difference,
                'percent_change': percent_change,
                'old_text': old_text,
                'new_text': new_text
            }
        
        return None
    
    def _compare_semantic(self, old_doc_data: Dict[str, Any], new_doc_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Perform semantic comparison of document content
        
        This is the original comparison logic, now separated from price detection
        
        Args:
            old_doc_data: Parsed data from old PAPL
            new_doc_data: Parsed data from new PAPL
            
        Returns:
            Dict with semantic changes (rules, guidance, structure)
        """
        result = {
            'business_rule_changes': [],
            'guidance_changes': [],
            'structural_changes': {
                'sections_added': [],
                'sections_removed': [],
                'sections_modified': []
            },
            'table_changes': {
                'tables_added': [],
                'tables_removed': [],
                'tables_modified': []
            },
            'summary': {}
        }
        
        # Compare business rules
        result['business_rule_changes'] = self._compare_rules(
            old_doc_data.get('business_rules', {}),
            new_doc_data.get('business_rules', {})
        )
        
        # Compare guidance
        result['guidance_changes'] = self._compare_guidance(
            old_doc_data.get('guidance', {}),
            new_doc_data.get('guidance', {})
        )
        
        # Compare structure (sections)
        result['structural_changes'] = self._compare_structure(
            old_doc_data.get('raw_paragraphs', []),
            new_doc_data.get('raw_paragraphs', [])
        )
        
        # Compare tables (non-pricing aspects)
        result['table_changes'] = self._compare_tables(
            old_doc_data.get('raw_tables', []),
            new_doc_data.get('raw_tables', [])
        )
        
        # Generate summary
        result['summary'] = self._generate_summary(result)
        
        return result
    
    def _compare_rules(self, old_rules: Dict, new_rules: Dict) -> List[Dict[str, Any]]:
        """Compare business rules between documents"""
        changes = []
        
        # Convert rules to comparable format
        old_rule_list = self._flatten_rules(old_rules)
        new_rule_list = self._flatten_rules(new_rules)
        
        # Find modified and removed rules
        for old_rule in old_rule_list:
            best_match = self._find_best_match(old_rule, new_rule_list)
            
            if best_match:
                # Check if content changed
                similarity = fuzz.ratio(old_rule['text'], best_match['text'])
                if similarity < 100:  # Changed
                    changes.append({
                        'type': 'modified',
                        'old_rule': old_rule,
                        'new_rule': best_match,
                        'similarity': similarity
                    })
            else:
                # Removed
                changes.append({
                    'type': 'removed',
                    'rule': old_rule
                })
        
        # Find added rules
        for new_rule in new_rule_list:
            best_match = self._find_best_match(new_rule, old_rule_list)
            if not best_match:
                changes.append({
                    'type': 'added',
                    'rule': new_rule
                })
        
        return changes
    
    def _compare_guidance(self, old_guidance: Dict, new_guidance: Dict) -> List[Dict[str, Any]]:
        """Compare guidance text between documents"""
        changes = []
        
        # Similar logic to rules comparison
        old_guidance_list = self._flatten_guidance(old_guidance)
        new_guidance_list = self._flatten_guidance(new_guidance)
        
        # Find modified and removed guidance
        for old_item in old_guidance_list:
            best_match = self._find_best_match(old_item, new_guidance_list)
            
            if best_match:
                similarity = fuzz.ratio(old_item['text'], best_match['text'])
                if similarity < 100:
                    changes.append({
                        'type': 'modified',
                        'old_guidance': old_item,
                        'new_guidance': best_match,
                        'similarity': similarity
                    })
            else:
                changes.append({
                    'type': 'removed',
                    'guidance': old_item
                })
        
        # Find added guidance
        for new_item in new_guidance_list:
            best_match = self._find_best_match(new_item, old_guidance_list)
            if not best_match:
                changes.append({
                    'type': 'added',
                    'guidance': new_item
                })
        
        return changes
    
    def _compare_structure(self, old_paragraphs: List[Dict], new_paragraphs: List[Dict]) -> Dict[str, List]:
        """Compare document structure (sections/headings)"""
        old_sections = [p for p in old_paragraphs if p.get('is_heading')]
        new_sections = [p for p in new_paragraphs if p.get('is_heading')]
        
        sections_added = []
        sections_removed = []
        sections_modified = []
        
        # Find removed and modified sections
        for old_section in old_sections:
            best_match = self._find_best_match(old_section, new_sections)
            
            if best_match:
                similarity = fuzz.ratio(old_section['text'], best_match['text'])
                if similarity < 100:
                    sections_modified.append({
                        'old_section': old_section,
                        'new_section': best_match,
                        'similarity': similarity
                    })
            else:
                sections_removed.append(old_section)
        
        # Find added sections
        for new_section in new_sections:
            best_match = self._find_best_match(new_section, old_sections)
            if not best_match:
                sections_added.append(new_section)
        
        return {
            'sections_added': sections_added,
            'sections_removed': sections_removed,
            'sections_modified': sections_modified
        }
    
    def _compare_tables(self, old_tables: List[Dict], new_tables: List[Dict]) -> Dict[str, List]:
        """Compare table structure (not pricing - that's handled separately)"""
        tables_added = []
        tables_removed = []
        tables_modified = []
        
        # Simple comparison by position for now
        max_tables = min(len(old_tables), len(new_tables))
        
        for i in range(max_tables):
            old_table = old_tables[i]
            new_table = new_tables[i]
            
            # Check if structure changed
            old_rows = len(old_table.get('data', []))
            new_rows = len(new_table.get('data', []))
            old_cols = len(old_table.get('data', [[]])[0]) if old_table.get('data') else 0
            new_cols = len(new_table.get('data', [[]])[0]) if new_table.get('data') else 0
            
            if old_rows != new_rows or old_cols != new_cols:
                tables_modified.append({
                    'table_index': i,
                    'old_dimensions': (old_rows, old_cols),
                    'new_dimensions': (new_rows, new_cols)
                })
        
        # Check for added/removed tables
        if len(new_tables) > len(old_tables):
            tables_added = list(range(len(old_tables), len(new_tables)))
        elif len(old_tables) > len(new_tables):
            tables_removed = list(range(len(new_tables), len(old_tables)))
        
        return {
            'tables_added': tables_added,
            'tables_removed': tables_removed,
            'tables_modified': tables_modified
        }
    
    def _flatten_rules(self, rules: Dict) -> List[Dict[str, Any]]:
        """Convert nested rules structure to flat list"""
        flat_rules = []
        
        if isinstance(rules, dict):
            for category, rule_list in rules.items():
                if isinstance(rule_list, list):
                    for rule in rule_list:
                        if isinstance(rule, dict):
                            flat_rules.append({
                                'category': category,
                                'text': rule.get('text', str(rule)),
                                'original': rule
                            })
                        else:
                            flat_rules.append({
                                'category': category,
                                'text': str(rule),
                                'original': rule
                            })
        
        return flat_rules
    
    def _flatten_guidance(self, guidance: Dict) -> List[Dict[str, Any]]:
        """Convert nested guidance structure to flat list"""
        flat_guidance = []
        
        if isinstance(guidance, dict):
            for section, content in guidance.items():
                if isinstance(content, list):
                    for item in content:
                        flat_guidance.append({
                            'section': section,
                            'text': str(item),
                            'original': item
                        })
                else:
                    flat_guidance.append({
                        'section': section,
                        'text': str(content),
                        'original': content
                    })
        
        return flat_guidance
    
    def _find_best_match(self, item: Dict[str, Any], candidate_list: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """
        Find best matching item in candidate list
        
        Args:
            item: Item to match
            candidate_list: List of candidates to match against
            
        Returns:
            Best matching item or None if no good match found
        """
        if not candidate_list:
            return None
        
        best_match = None
        best_score = 0
        
        item_text = item.get('text', '')
        
        for candidate in candidate_list:
            candidate_text = candidate.get('text', '')
            score = fuzz.ratio(item_text, candidate_text)
            
            if score > best_score and score >= self.similarity_threshold:
                best_score = score
                best_match = candidate
        
        return best_match
    
    def _generate_summary(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Generate summary statistics from comparison results"""
        summary = {
            'total_rule_changes': len(results.get('business_rule_changes', [])),
            'total_guidance_changes': len(results.get('guidance_changes', [])),
            'sections_added': len(results.get('structural_changes', {}).get('sections_added', [])),
            'sections_removed': len(results.get('structural_changes', {}).get('sections_removed', [])),
            'sections_modified': len(results.get('structural_changes', {}).get('sections_modified', [])),
            'tables_added': len(results.get('table_changes', {}).get('tables_added', [])),
            'tables_removed': len(results.get('table_changes', {}).get('tables_removed', [])),
            'tables_modified': len(results.get('table_changes', {}).get('tables_modified', []))
        }
        
        # Count changes by type
        rule_changes = results.get('business_rule_changes', [])
        summary['rules_added'] = sum(1 for r in rule_changes if r['type'] == 'added')
        summary['rules_removed'] = sum(1 for r in rule_changes if r['type'] == 'removed')
        summary['rules_modified'] = sum(1 for r in rule_changes if r['type'] == 'modified')
        
        guidance_changes = results.get('guidance_changes', [])
        summary['guidance_added'] = sum(1 for g in guidance_changes if g['type'] == 'added')
        summary['guidance_removed'] = sum(1 for g in guidance_changes if g['type'] == 'removed')
        summary['guidance_modified'] = sum(1 for g in guidance_changes if g['type'] == 'modified')
        
        return summary
    
    def format_price_change(self, change: Dict[str, Any]) -> str:
        """
        Format a price change for display
        
        Args:
            change: Price change dictionary
            
        Returns:
            Formatted string for display
            
        Example:
            "Item 01_001: $50.00 → $55.00 (+$5.00, +10.0%)"
        """
        item = change.get('item_number', 'Unknown')
        desc = change.get('item_description', '')
        old = change['old_price']
        new = change['new_price']
        diff = change['difference']
        pct = change['percent_change']
        
        # Format difference with sign
        diff_str = f"+${diff:.2f}" if diff > 0 else f"-${abs(diff):.2f}"
        pct_str = f"+{pct:.1f}%" if pct > 0 else f"{pct:.1f}%"
        
        # Build display string
        result = f"Item {item}"
        if desc:
            result += f" ({desc[:50]}...)" if len(desc) > 50 else f" ({desc})"
        result += f": ${old:.2f} → ${new:.2f} ({diff_str}, {pct_str})"
        
        return result
    
    def export_results(self, results: Dict[str, Any], output_path: str):
        """
        Export comparison results to JSON file
        
        Args:
            results: Comparison results dictionary
            output_path: Path to save JSON file
        """
        with open(output_path, 'w') as f:
            json.dump(results, f, indent=2, default=str)