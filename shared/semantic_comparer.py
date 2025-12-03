"""
Semantic PAPL Comparison Engine
Compares parsed PAPL structures (not just raw text)
"""

from typing import Dict, List, Any
import difflib


class SemanticComparer:
    """
    Compare two parsed PAPL documents semantically
    
    Compares:
    - Pricing data (items, prices, categories)
    - Business rules (conditions, requirements)
    - Guidance text (sections, content)
    - Table structures (rows, columns, content)
    """
    
    def compare(self, old_parsed: Dict, new_parsed: Dict) -> Dict[str, Any]:
        """
        Perform complete semantic comparison
        
        Args:
            old_parsed: Output from PAPLParser.parse() for old version
            new_parsed: Output from PAPLParser.parse() for new version
        
        Returns:
            Comprehensive comparison results
        """
        return {
            'pricing_changes': self.compare_pricing(
                old_parsed['pricing_data'],
                new_parsed['pricing_data']
            ),
            'rule_changes': self.compare_rules(
                old_parsed['business_rules'],
                new_parsed['business_rules']
            ),
            'guidance_changes': self.compare_guidance(
                old_parsed['guidance'],
                new_parsed['guidance']
            ),
            'table_structure_changes': self.compare_table_structures(
                old_parsed['raw_tables'],
                new_parsed['raw_tables']
            ),
            'metadata': {
                'old_version': old_parsed['metadata'],
                'new_version': new_parsed['metadata']
            }
        }
    
    def compare_pricing(self, old_pricing: Dict, new_pricing: Dict) -> Dict[str, Any]:
        """Compare pricing data"""
        changes = {
            'summary': {
                'tables_added': 0,
                'tables_removed': 0,
                'tables_modified': 0,
                'items_added': 0,
                'items_removed': 0,
                'prices_changed': 0
            },
            'details': []
        }
        
        old_tables = {t['table_index']: t for t in old_pricing['tables']}
        new_tables = {t['table_index']: t for t in new_pricing['tables']}
        
        # Find table changes
        all_indices = set(old_tables.keys()) | set(new_tables.keys())
        
        for idx in sorted(all_indices):
            if idx not in old_tables:
                changes['summary']['tables_added'] += 1
                changes['details'].append({
                    'type': 'table_added',
                    'table_index': idx,
                    'items_count': len(new_tables[idx]['items'])
                })
            elif idx not in new_tables:
                changes['summary']['tables_removed'] += 1
                changes['details'].append({
                    'type': 'table_removed',
                    'table_index': idx,
                    'items_count': len(old_tables[idx]['items'])
                })
            else:
                # Compare items within table
                table_changes = self._compare_pricing_items(
                    old_tables[idx]['items'],
                    new_tables[idx]['items'],
                    idx
                )
                if table_changes:
                    changes['summary']['tables_modified'] += 1
                    changes['summary']['items_added'] += len(table_changes.get('added', []))
                    changes['summary']['items_removed'] += len(table_changes.get('removed', []))
                    changes['summary']['prices_changed'] += len(table_changes.get('prices_changed', []))
                    changes['details'].append({
                        'type': 'table_modified',
                        'table_index': idx,
                        'changes': table_changes
                    })
        
        return changes
    
    def _compare_pricing_items(self, old_items: List, new_items: List, table_idx: int) -> Dict:
        """Compare pricing items within a table"""
        changes = {
            'added': [],
            'removed': [],
            'prices_changed': [],
            'modified': []
        }
        
        # Create lookup by item name
        old_by_name = {item['item_name']: item for item in old_items if item['item_name']}
        new_by_name = {item['item_name']: item for item in new_items if item['item_name']}
        
        # Find added items
        for name in set(new_by_name.keys()) - set(old_by_name.keys()):
            item = new_by_name[name]
            changes['added'].append({
                'item_name': name,
                'price': item['price'],
                'row_data': item['row_data'],
                'location': item.get('location', {}),  # NEW: Include location
                'context': self._get_row_context(new_items, name)  # NEW: Add context
            })
        
        # Find removed items
        for name in set(old_by_name.keys()) - set(new_by_name.keys()):
            item = old_by_name[name]
            changes['removed'].append({
                'item_name': name,
                'price': item['price'],
                'row_data': item['row_data'],
                'location': item.get('location', {}),  # NEW: Include location
                'context': self._get_row_context(old_items, name)  # NEW: Add context
            })
        
        # Find modified items
        for name in set(old_by_name.keys()) & set(new_by_name.keys()):
            old_item = old_by_name[name]
            new_item = new_by_name[name]
            
            if old_item['price'] != new_item['price']:
                changes['prices_changed'].append({
                    'item_name': name,
                    'old_price': old_item['price'],
                    'new_price': new_item['price'],
                    'old_location': old_item.get('location', {}),  # NEW: Old location
                    'new_location': new_item.get('location', {}),  # NEW: New location
                    'change': self._calculate_price_change(old_item['price'], new_item['price']),
                    'old_context': self._get_row_context(old_items, name),  # NEW: Context
                    'new_context': self._get_row_context(new_items, name)   # NEW: Context
                })
            elif old_item['row_data'] != new_item['row_data']:
                changes['modified'].append({
                    'item_name': name,
                    'old_data': old_item['row_data'],
                    'new_data': new_item['row_data'],
                    'old_location': old_item.get('location', {}),  # NEW: Old location
                    'new_location': new_item.get('location', {}),  # NEW: New location
                    'old_context': self._get_row_context(old_items, name),  # NEW: Context
                    'new_context': self._get_row_context(new_items, name)   # NEW: Context
                })
        
        return changes if any(changes.values()) else None
    
    def _calculate_price_change(self, old_price: str, new_price: str) -> Dict:
        """Calculate price change percentage"""
        try:
            old_val = float(old_price.replace('$', '').replace(',', ''))
            new_val = float(new_price.replace('$', '').replace(',', ''))
            diff = new_val - old_val
            percent = (diff / old_val * 100) if old_val != 0 else 0
            return {
                'absolute': f"${diff:,.2f}",
                'percentage': f"{percent:+.1f}%"
            }
        except:
            return {'absolute': 'N/A', 'percentage': 'N/A'}
    
    def compare_rules(self, old_rules: Dict, new_rules: Dict) -> Dict[str, Any]:
        """Compare business rules"""
        changes = {
            'summary': {
                'rules_added': 0,
                'rules_removed': 0,
                'rules_modified': 0,
                'high_priority_changes': 0
            },
            'details': []
        }
        
        old_rule_texts = {r['text']: r for r in old_rules['rules']}
        new_rule_texts = {r['text']: r for r in new_rules['rules']}
        
        # Find added rules
        for text in set(new_rule_texts.keys()) - set(old_rule_texts.keys()):
            rule = new_rule_texts[text]
            changes['summary']['rules_added'] += 1
            if rule['priority'] == 'high':
                changes['summary']['high_priority_changes'] += 1
            changes['details'].append({
                'type': 'rule_added',
                'text': text[:200] + '...' if len(text) > 200 else text,
                'rule_type': rule['type'],
                'priority': rule['priority'],
                'conditions': rule['conditions'],
                'location': rule.get('location', {})  # NEW: Include location
            })
        
        # Find removed rules
        for text in set(old_rule_texts.keys()) - set(new_rule_texts.keys()):
            rule = old_rule_texts[text]
            changes['summary']['rules_removed'] += 1
            if rule['priority'] == 'high':
                changes['summary']['high_priority_changes'] += 1
            changes['details'].append({
                'type': 'rule_removed',
                'text': text[:200] + '...' if len(text) > 200 else text,
                'rule_type': rule['type'],
                'priority': rule['priority'],
                'location': rule.get('location', {})  # NEW: Include location
            })
        
        # Find modified rules (similar but not identical)
        # Using fuzzy matching for rules that might have minor wording changes
        remaining_old = set(old_rule_texts.keys()) - set(new_rule_texts.keys())
        remaining_new = set(new_rule_texts.keys()) - set(old_rule_texts.keys())
        
        for old_text in remaining_old:
            for new_text in remaining_new:
                similarity = difflib.SequenceMatcher(None, old_text, new_text).ratio()
                if similarity > 0.7:  # 70% similar
                    changes['summary']['rules_modified'] += 1
                    changes['details'].append({
                        'type': 'rule_modified',
                        'old_text': old_text[:200] + '...' if len(old_text) > 200 else old_text,
                        'new_text': new_text[:200] + '...' if len(new_text) > 200 else new_text,
                        'similarity': f"{similarity:.1%}",
                        'old_location': old_rule_texts[old_text].get('location', {}),  # NEW: Location
                        'new_location': new_rule_texts[new_text].get('location', {})   # NEW: Location
                    })
                    break
        
        return changes
    
    def compare_guidance(self, old_guidance: Dict, new_guidance: Dict) -> Dict[str, Any]:
        """Compare guidance sections"""
        changes = {
            'summary': {
                'sections_added': 0,
                'sections_removed': 0,
                'sections_modified': 0,
                'word_count_change': new_guidance['word_count'] - old_guidance['word_count']
            },
            'details': []
        }
        
        old_sections = {s['heading']: s for s in old_guidance['sections']}
        new_sections = {s['heading']: s for s in new_guidance['sections']}
        
        # Find added sections
        for heading in set(new_sections.keys()) - set(old_sections.keys()):
            section = new_sections[heading]
            changes['summary']['sections_added'] += 1
            changes['details'].append({
                'type': 'section_added',
                'heading': heading,
                'paragraph_count': len(section['paragraphs']),
                'location': section.get('location', {})  # NEW: Include location
            })
        
        # Find removed sections
        for heading in set(old_sections.keys()) - set(new_sections.keys()):
            section = old_sections[heading]
            changes['summary']['sections_removed'] += 1
            changes['details'].append({
                'type': 'section_removed',
                'heading': heading,
                'paragraph_count': len(section['paragraphs']),
                'location': section.get('location', {})  # NEW: Include location
            })
        
        # Find modified sections
        for heading in set(old_sections.keys()) & set(new_sections.keys()):
            old_section = old_sections[heading]
            new_section = new_sections[heading]
            old_text = ' '.join(p['text'] for p in old_section['paragraphs'])
            new_text = ' '.join(p['text'] for p in new_section['paragraphs'])
            
            if old_text != new_text:
                changes['summary']['sections_modified'] += 1
                changes['details'].append({
                    'type': 'section_modified',
                    'heading': heading,
                    'old_length': len(old_text.split()),
                    'new_length': len(new_text.split()),
                    'change_type': self._classify_text_change(old_text, new_text),
                    'old_location': old_section.get('location', {}),  # NEW: Location
                    'new_location': new_section.get('location', {}),  # NEW: Location
                    'paragraph_changes': self._compare_section_paragraphs(  # NEW: Detailed paragraph changes
                        old_section['paragraphs'],
                        new_section['paragraphs']
                    )
                })
        
        return changes
    
    def _classify_text_change(self, old_text: str, new_text: str) -> str:
        """Classify type of text change"""
        old_len = len(old_text.split())
        new_len = len(new_text.split())
        
        diff_percent = abs(new_len - old_len) / old_len * 100 if old_len > 0 else 100
        
        if diff_percent > 50:
            return 'major_rewrite'
        elif diff_percent > 20:
            return 'significant_change'
        else:
            return 'minor_edit'
    
    def compare_table_structures(self, old_tables: List, new_tables: List) -> Dict[str, Any]:
        """Compare table structures (rows, columns, dimensions)"""
        changes = {
            'summary': {
                'tables_added': 0,
                'tables_removed': 0,
                'structure_changed': 0,
                'content_changed': 0
            },
            'details': []
        }
        
        # Compare by index
        max_index = max(len(old_tables), len(new_tables))
        
        for i in range(max_index):
            if i >= len(old_tables):
                changes['summary']['tables_added'] += 1
                changes['details'].append({
                    'type': 'table_added',
                    'table_index': i,
                    'rows': new_tables[i]['rows'],
                    'cols': new_tables[i]['cols']
                })
            elif i >= len(new_tables):
                changes['summary']['tables_removed'] += 1
                changes['details'].append({
                    'type': 'table_removed',
                    'table_index': i,
                    'rows': old_tables[i]['rows'],
                    'cols': old_tables[i]['cols']
                })
            else:
                # Compare structure
                old_table = old_tables[i]
                new_table = new_tables[i]
                
                structure_changed = (
                    old_table['rows'] != new_table['rows'] or
                    old_table['cols'] != new_table['cols']
                )
                
                content_changed = old_table['data'] != new_table['data']
                
                if structure_changed or content_changed:
                    if structure_changed:
                        changes['summary']['structure_changed'] += 1
                    if content_changed:
                        changes['summary']['content_changed'] += 1
                    
                    changes['details'].append({
                        'type': 'table_modified',
                        'table_index': i,
                        'structure_changed': structure_changed,
                        'old_dimensions': {'rows': old_table['rows'], 'cols': old_table['cols']},
                        'new_dimensions': {'rows': new_table['rows'], 'cols': new_table['cols']},
                        'row_diff': new_table['rows'] - old_table['rows'],
                        'col_diff': new_table['cols'] - old_table['cols']
                    })
        
        return changes
    
    def _compare_section_paragraphs(self, old_paragraphs: List[Dict], new_paragraphs: List[Dict]) -> Dict:
        """
        Compare paragraphs within a section in detail
        
        Args:
            old_paragraphs: List of paragraphs from old section
            new_paragraphs: List of paragraphs from new section
        
        Returns:
            Dict with detailed paragraph-level changes
        """
        # Simple comparison - could be enhanced with fuzzy matching
        old_texts = {p['text']: p for p in old_paragraphs}
        new_texts = {p['text']: p for p in new_paragraphs}
        
        added = []
        for text in set(new_texts.keys()) - set(old_texts.keys()):
            para = new_texts[text]
            added.append({
                'text': text[:200] + '...' if len(text) > 200 else text,
                'location': para.get('location', {})
            })
        
        removed = []
        for text in set(old_texts.keys()) - set(new_texts.keys()):
            para = old_texts[text]
            removed.append({
                'text': text[:200] + '...' if len(text) > 200 else text,
                'location': para.get('location', {})
            })
        
        return {
            'paragraphs_added': len(added),
            'paragraphs_removed': len(removed),
            'added_details': added,
            'removed_details': removed
        }
    
    def _get_row_context(self, items: List[Dict], item_name: str, context_size: int = 2) -> Dict:
        """
        Get surrounding rows for context
        
        Args:
            items: List of pricing items
            item_name: Name of the item to find context for
            context_size: Number of rows before and after to include
        
        Returns:
            Dict with before/after context
        """
        # Find the item's position
        item_idx = None
        for idx, item in enumerate(items):
            if item['item_name'] == item_name:
                item_idx = idx
                break
        
        if item_idx is None:
            return {'before': [], 'after': []}
        
        # Get surrounding items
        start_idx = max(0, item_idx - context_size)
        end_idx = min(len(items), item_idx + context_size + 1)
        
        before_items = []
        for i in range(start_idx, item_idx):
            before_items.append({
                'item_name': items[i]['item_name'],
                'price': items[i]['price'],
                'location': items[i].get('location', {})
            })
        
        after_items = []
        for i in range(item_idx + 1, end_idx):
            after_items.append({
                'item_name': items[i]['item_name'],
                'price': items[i]['price'],
                'location': items[i].get('location', {})
            })
        
        return {
            'before': before_items,
            'after': after_items
        }
    
    def _get_paragraph_context(self, paragraphs: List[Dict], para_index: int, context_size: int = 2) -> Dict:
        """
        Get surrounding paragraphs for context
        
        Args:
            paragraphs: List of paragraphs from guidance or rules
            para_index: Index of the paragraph to find context for
            context_size: Number of paragraphs before and after to include
        
        Returns:
            Dict with before/after context
        """
        # Get surrounding paragraphs
        start_idx = max(0, para_index - context_size)
        end_idx = min(len(paragraphs), para_index + context_size + 1)
        
        before_paras = []
        for i in range(start_idx, para_index):
            before_paras.append({
                'text': paragraphs[i]['text'][:200] + '...' if len(paragraphs[i]['text']) > 200 else paragraphs[i]['text'],
                'location': paragraphs[i].get('location', {})
            })
        
        after_paras = []
        for i in range(para_index + 1, end_idx):
            after_paras.append({
                'text': paragraphs[i]['text'][:200] + '...' if len(paragraphs[i]['text']) > 200 else paragraphs[i]['text'],
                'location': paragraphs[i].get('location', {})
            })
        
        return {
            'before': before_paras,
            'after': after_paras
        }


# Example usage
if __name__ == "__main__":
    comparer = SemanticComparer()
    
    # Compare two parsed PAPL documents
    # comparison = comparer.compare(old_parsed_data, new_parsed_data)
    
    print("Semantic Comparer ready!")