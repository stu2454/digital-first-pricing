"""
Semantic PAPL Parser
Extracts structured data from PAPL .docx documents

Outputs:
- pricing_data.json: Support items, prices, categories
- business_rules.yaml: Claiming rules, conditions, logic
- guidance.md: Policy text, explanations, requirements

ENHANCED: Now includes numerical price detection and comparison
"""

from docx import Document
import json
import yaml
from typing import Dict, List, Any, Tuple, Optional
import re
from datetime import datetime


class PAPLParser:
    """
    Parse PAPL documents into structured components
    
    Philosophy: PAPL contains three types of content:
    1. Pricing Data - Tables with support items and prices
    2. Business Rules - Conditions, thresholds, requirements
    3. Guidance - Explanatory text, policy context
    """
    
    def __init__(self):
        self.pricing_keywords = [
            'price', 'rate', 'cost', 'fee', 'charge', 'amount',
            'support item', 'support category', 'registration group'
        ]
        
        self.rule_keywords = [
            'must', 'should', 'shall', 'may not', 'required', 'mandatory',
            'condition', 'threshold', 'limit', 'maximum', 'minimum',
            'claiming', 'quote', 'evidence', 'approval'
        ]
        
        self.guidance_keywords = [
            'guidance', 'note', 'example', 'information', 'consider',
            'background', 'context', 'purpose', 'overview'
        ]
    
    def parse(self, docx_path_or_file) -> Dict[str, Any]:
        """
        Parse PAPL document into structured components
        
        Args:
            docx_path_or_file: Path to .docx or file-like object
        
        Returns:
            Dict with 'pricing_data', 'business_rules', 'guidance', 'metadata'
        """
        doc = Document(docx_path_or_file)
        
        # Extract all content with metadata
        paragraphs = self._extract_paragraphs(doc)
        tables = self._extract_tables(doc)
        
        # Classify and structure content
        pricing_data = self._extract_pricing_data(tables, paragraphs)
        business_rules = self._extract_business_rules(paragraphs, tables)
        guidance = self._extract_guidance(paragraphs)
        
        # Generate metadata
        metadata = self._generate_metadata(doc, paragraphs, tables)
        
        return {
            'pricing_data': pricing_data,
            'business_rules': business_rules,
            'guidance': guidance,
            'metadata': metadata,
            'raw_tables': tables,
            'raw_paragraphs': paragraphs
        }
    
    def _extract_paragraphs(self, doc: Document) -> List[Dict[str, Any]]:
        """Extract paragraphs with metadata"""
        paragraphs = []
        for i, para in enumerate(doc.paragraphs):
            if not para.text.strip():
                continue
            
            paragraphs.append({
                'index': i,
                'text': para.text.strip(),
                'style': para.style.name if para.style else 'Normal',
                'is_heading': 'Heading' in (para.style.name if para.style else ''),
                'level': self._get_heading_level(para.style.name if para.style else '')
            })
        
        return paragraphs
    
    def _get_heading_level(self, style_name: str) -> int:
        """
        Extract heading level from style name
        
        Args:
            style_name: Style name like 'Heading 1', 'Heading 2', etc.
            
        Returns:
            Heading level (1-9) or 0 if not a heading
        """
        if not style_name or 'Heading' not in style_name:
            return 0
        
        # Extract number from style name
        match = re.search(r'Heading\s*(\d+)', style_name)
        if match:
            return int(match.group(1))
        
        return 0
    
    def _extract_tables(self, doc: Document) -> List[Dict[str, Any]]:
        """Extract tables with full data, row numbering, and pricing metadata"""
        tables = []
        for i, table in enumerate(doc.tables):
            rows = []
            for row in table.rows:
                cells = [cell.text.strip() for cell in row.cells]
                rows.append(cells)
            
            # Create table dict
            table_dict = {
                'index': i,
                'row_count': len(rows),
                'col_count': len(rows[0]) if rows else 0,
                'data': rows
            }
            
            # Add pricing metadata
            is_pricing, confidence = self._is_pricing_table(table_dict)
            
            table_dict['is_pricing_table'] = is_pricing
            table_dict['pricing_confidence'] = confidence
            
            # Classify table type
            table_dict['table_type'] = self._classify_table_type(table_dict, is_pricing, confidence)
            
            # Add headers for easy reference
            if rows:
                table_dict['headers'] = rows[0]
            else:
                table_dict['headers'] = []
            
            tables.append(table_dict)
        
        return tables
    
    def _classify_table_type(self, table_dict: Dict[str, Any], is_pricing: bool, confidence: int) -> str:
        """Classify what type of table this is"""
        if is_pricing and confidence >= 60:
            return 'pricing'
        
        headers = [str(h).lower() for h in table_dict.get('headers', [])]
        header_text = ' '.join(headers)
        row_count = table_dict.get('row_count', 0) - 1  # Exclude header
        
        # Check for example tables
        if row_count <= 5:
            # Look at cell content for long narrative
            data = table_dict.get('data', [])
            for row in data[1:]:  # Skip header
                for cell in row:
                    if len(str(cell)) > 500:
                        return 'example'
        
        # Check for reference tables
        if any(keyword in header_text for keyword in ['mmm', 'postcode', 'location', 'state', 'zone']):
            return 'reference'
        
        # Check for metadata tables
        if any(keyword in header_text for keyword in ['version', 'date published', 'amendment', 'page(s)']):
            return 'metadata'
        
        return 'other'
    
    
    def _extract_pricing_data(self, tables: List[Dict], paragraphs: List[Dict]) -> Dict[str, Any]:
        """Extract pricing data from tables"""
        pricing_data = {
            'support_items': [],
            'categories': set(),
            'total_items': 0
        }
        
        for table in tables:
            # Check if this looks like a pricing table
            if not table['data'] or len(table['data']) < 2:
                continue
            
            # Get headers (first row)
            headers = [str(h).lower() for h in table['data'][0]]
            
            # Look for pricing-related columns
            has_pricing = any(keyword in ' '.join(headers) for keyword in self.pricing_keywords)
            
            if has_pricing:
                # Process data rows
                for row_idx, row in enumerate(table['data'][1:], start=1):
                    if len(row) < 2:
                        continue
                    
                    item = {
                        'table_index': table['index'],
                        'row_index': row_idx,
                        'data': row,
                        'price': self._extract_price(row),
                        'item_number': self._extract_item_number(' '.join(str(c) for c in row))
                    }
                    
                    pricing_data['support_items'].append(item)
        
        pricing_data['total_items'] = len(pricing_data['support_items'])
        pricing_data['categories'] = list(pricing_data['categories'])
        
        return pricing_data
    
    def _extract_business_rules(self, paragraphs: List[Dict], tables: List[Dict]) -> Dict[str, Any]:
        """Extract business rules from paragraphs"""
        rules = {
            'claiming_rules': [],
            'conditions': [],
            'thresholds': [],
            'total_rules': 0
        }
        
        for para in paragraphs:
            text_lower = para['text'].lower()
            
            # Check if paragraph contains rule keywords
            has_rule_keywords = any(keyword in text_lower for keyword in self.rule_keywords)
            
            if has_rule_keywords:
                rule = {
                    'paragraph_index': para['index'],
                    'text': para['text'],
                    'type': self._classify_rule(para['text'])
                }
                
                if 'claiming' in text_lower or 'claim' in text_lower:
                    rules['claiming_rules'].append(rule)
                elif any(word in text_lower for word in ['condition', 'if', 'when']):
                    rules['conditions'].append(rule)
                elif any(word in text_lower for word in ['threshold', 'limit', 'maximum', 'minimum']):
                    rules['thresholds'].append(rule)
        
        rules['total_rules'] = (len(rules['claiming_rules']) + 
                                len(rules['conditions']) + 
                                len(rules['thresholds']))
        
        return rules
    
    def _extract_guidance(self, paragraphs: List[Dict]) -> Dict[str, Any]:
        """Extract guidance text"""
        guidance = {
            'sections': [],
            'markdown': '',
            'total_paragraphs': 0
        }
        
        current_section = None
        
        for para in paragraphs:
            if para['is_heading']:
                if current_section:
                    guidance['sections'].append(current_section)
                
                current_section = {
                    'title': para['text'],
                    'level': para['level'],
                    'paragraphs': []
                }
            else:
                text_lower = para['text'].lower()
                has_guidance = any(keyword in text_lower for keyword in self.guidance_keywords)
                
                # Add to current section if it looks like guidance
                if has_guidance or (current_section and len(para['text']) > 50):
                    if current_section:
                        current_section['paragraphs'].append(para['text'])
        
        if current_section:
            guidance['sections'].append(current_section)
        
        # Generate markdown
        guidance['markdown'] = self._generate_markdown(guidance['sections'])
        guidance['total_paragraphs'] = sum(len(s['paragraphs']) for s in guidance['sections'])
        
        return guidance
    
    def _classify_rule(self, text: str) -> str:
        """Classify type of rule"""
        text_lower = text.lower()
        
        if 'must' in text_lower or 'shall' in text_lower or 'required' in text_lower:
            return 'mandatory'
        elif 'should' in text_lower or 'recommended' in text_lower:
            return 'recommended'
        elif 'may' in text_lower or 'can' in text_lower:
            return 'optional'
        else:
            return 'informational'
    
    def _generate_metadata(self, doc: Document, paragraphs: List[Dict], tables: List[Dict]) -> Dict[str, Any]:
        """Generate document metadata"""
        return {
            'parsed_at': datetime.now().isoformat(),
            'total_paragraphs': len(paragraphs),
            'total_tables': len(tables),
            'total_headings': sum(1 for p in paragraphs if p['is_heading']),
            'document_length': sum(len(p['text']) for p in paragraphs)
        }
    
    def _generate_markdown(self, sections: List[Dict]) -> str:
        """Generate markdown from guidance sections"""
        md_lines = []
        
        for section in sections:
            # Add heading
            heading_prefix = '#' * section['level'] if section['level'] > 0 else '##'
            md_lines.append(f"{heading_prefix} {section['title']}\n")
            
            # Add paragraphs
            for para in section['paragraphs']:
                md_lines.append(f"{para}\n")
            
            md_lines.append("")  # Blank line between sections
        
        return '\n'.join(md_lines)
    
    # ===== Export Functions =====
    
    def export_to_json(self, parsed_data: Dict[str, Any]) -> str:
        """Export pricing data to JSON"""
        export_data = {
            'pricing_data': parsed_data['pricing_data'],
            'metadata': parsed_data['metadata']
        }
        return json.dumps(export_data, indent=2)
    
    def export_to_yaml(self, parsed_data: Dict[str, Any]) -> str:
        """Export business rules to YAML"""
        export_data = {
            'business_rules': parsed_data['business_rules'],
            'metadata': {
                'parsed_at': parsed_data['metadata']['parsed_at'],
                'total_rules': parsed_data['business_rules']['total_rules']
            }
        }
        return yaml.dump(export_data, default_flow_style=False, sort_keys=False)
    
    def export_to_markdown(self, parsed_data: Dict[str, Any]) -> str:
        """Export guidance to Markdown"""
        return parsed_data['guidance']['markdown']
    
    # ===== Price Detection Methods =====
    
    def _extract_price(self, item_or_row) -> Optional[float]:
        """
        Extract price from item, row, or text
        Handles various input types from different parts of parsing
        """
        text_to_search = ""
        
        # If it's a dict (row from table)
        if isinstance(item_or_row, dict):
            for key, value in item_or_row.items():
                text_to_search += str(value) + " "
        
        # If it's a list (row cells)
        elif isinstance(item_or_row, list):
            text_to_search = " ".join(str(cell) for cell in item_or_row)
        
        # If it's a string
        else:
            text_to_search = str(item_or_row)
        
        # Look for price pattern
        match = re.search(r'\$?\s*(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)', text_to_search)
        if match:
            try:
                return float(match.group(1).replace(',', ''))
            except:
                pass
        
        return None
    
    def _extract_all_prices(self, text: str) -> List[float]:
        """Extract all prices from text"""
        if not text:
            return []
        
        pattern = r'\$?\s*(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)'
        matches = re.findall(pattern, str(text))
        
        prices = []
        for match in matches:
            try:
                price = float(match.replace(',', ''))
                prices.append(price)
            except ValueError:
                continue
        
        return prices
    
    def _extract_item_number(self, text: str) -> Optional[str]:
        """Extract NDIS support item number from text"""
        if not text:
            return None
        
        # Pattern for NDIS item numbers (various formats)
        patterns = [
            r'(\d{2}_\d{3}_\d{4}_\d+_\d+)',  # Full format
            r'(\d{2}_\d{3}_\d{4})',          # Medium
            r'(\d{2}_\d{3})',                # Short
            r'(\d+\.\d+\.\d+)',              # Dot format
        ]
        
        for pattern in patterns:
            match = re.search(pattern, str(text))
            if match:
                return match.group(1)
        
        return None
    
    def _is_pricing_table(self, table: Dict[str, Any], context_paragraphs: List[Dict[str, Any]] = None) -> Tuple[bool, int]:
        """
        Enhanced pricing table detection that distinguishes real pricing tables
        from example/narrative tables
        
        Looks for:
        - Large number of rows (50+) - real tables have many items
        - Multiple price columns (National, Remote, Very Remote)
        - Structured item numbers
        - Penalizes long narrative text (example tables)
        
        Returns:
            Tuple of (is_pricing, confidence_score)
        """
        confidence_score = 0
        
        # Get table data
        data = table.get('data', [])
        if not data or len(data) < 2:  # Need at least header + 1 row
            return False, 0
        
        headers = [str(h).lower() for h in data[0]]
        header_text = ' '.join(headers)
        
        # CRITICAL CHECK 1: Table size (distinguishes real vs example tables)
        row_count = len(data) - 1  # Exclude header
        
        if row_count >= 50:
            # Large table - likely a real pricing table
            confidence_score += 40
        elif row_count >= 20:
            # Medium table - probably pricing
            confidence_score += 30
        elif row_count >= 10:
            # Small table - maybe pricing
            confidence_score += 20
        else:
            # Very small table - probably example/narrative
            confidence_score += 0
        
        # CRITICAL CHECK 2: Multiple price columns
        # Real pricing tables have National, Remote, Very Remote columns
        price_column_keywords = ['national', 'remote', 'very remote', 'price', 'rate', 'cost', 'limit', 'amount']
        price_columns = sum(1 for h in headers if any(keyword in h for keyword in price_column_keywords))
        
        if price_columns >= 3:
            # Multiple price columns - strong indicator (National, Remote, Very Remote)
            confidence_score += 40
        elif price_columns >= 2:
            # Two price columns
            confidence_score += 30
        elif price_columns >= 1:
            # One price column
            confidence_score += 20
        
        # CHECK 3: Has item numbers in correct format
        # Check first column for structured item numbers
        item_number_count = 0
        
        if len(data) > 1:
            # Sample first 5 rows
            for row in data[1:min(6, len(data))]:
                if row and len(row) > 0:
                    cell = str(row[0])
                    # Check for NDIS item number format: XX_XXX_XXXX_X_X
                    if self._extract_item_number(cell):
                        item_number_count += 1
            
            if item_number_count >= 3:  # At least 3 out of 5 rows
                confidence_score += 30
        
        # CHECK 4: Headers contain "item number" or similar
        if any(keyword in header_text for keyword in ['item number', 'support item', 'item name']):
            confidence_score += 10
        
        # CHECK 5: Has "unit" column (Each, Hour, etc.)
        if 'unit' in header_text:
            confidence_score += 10
        
        # CHECK 6: Context indicates pricing section
        if context_paragraphs:
            context_text = ' '.join([p.get('text', '').lower() for p in context_paragraphs[-3:]])
            if any(word in context_text for word in ['pricing', 'price', 'rate', 'cost']):
                confidence_score += 10
        
        # CHECK 7: Consistent numeric values in price columns
        if price_columns > 0 and row_count > 0:
            # Sample a few rows to check for dollar amounts
            price_cell_count = 0
            for row in data[1:min(6, len(data))]:
                for cell in row:
                    if self._extract_price(str(cell)):
                        price_cell_count += 1
            
            if price_cell_count >= 5:
                confidence_score += 10
        
        # PENALTY: Very long cell content suggests narrative/example table
        for row in data[1:min(6, len(data))]:
            for cell in row:
                if len(str(cell)) > 500:  # Very long text in cell
                    confidence_score -= 30
                    break
        
        # Ensure score doesn't go negative
        confidence_score = max(0, confidence_score)
        
        # Decision: threshold of 60
        return confidence_score >= 60, confidence_score
    
    def _extract_prices_from_table(self, table: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract all prices from a table with location info"""
        prices = []
        
        if not table.get('data'):
            return prices
        
        table_index = table.get('index', 0)
        
        # Skip header row, process data rows
        for row_idx, row in enumerate(table['data'][1:], start=1):
            
            # Try to find item number in this row
            item_number = None
            item_description = None
            
            for cell in row:
                cell_text = str(cell)
                
                if not item_number:
                    item_number = self._extract_item_number(cell_text)
                
                if not item_description and len(cell_text) > 10 and not self._extract_price(cell_text):
                    item_description = cell_text.strip()
            
            # Extract prices from this row (skip col 0 - item number column)
            for col_idx, cell in enumerate(row):
                cell_text = str(cell)
                
                # Skip column 0 (item number column) to avoid extracting numbers from item IDs
                if col_idx == 0:
                    continue
                    
                price = self._extract_price(cell_text)
                
                if price:
                    prices.append({
                        'table_index': table_index,
                        'item_number': item_number,
                        'item_description': item_description,
                        'price': price,
                        'row_index': row_idx,
                        'col_index': col_idx,
                        'raw_text': cell_text.strip()
                    })
        
        return prices
    
    def _compare_table_prices(self, old_table: Dict[str, Any], new_table: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Compare prices between two tables by item number"""
        changes = []
        
        # Extract prices from both tables
        old_prices = self._extract_prices_from_table(old_table)
        new_prices = self._extract_prices_from_table(new_table)
        
        # Build lookup by (item_number, column_index)
        # Each item can have multiple prices (National, Remote, Very Remote)
        
        # Group prices by item and column
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
        
        # Compare matching item+column pairs
        for key in old_by_item_col:
            if key in new_by_item_col:
                old_p = old_by_item_col[key]
                new_p = new_by_item_col[key]
                
                # Extract item number from key
                item_number, col_index = key
                
                # Only flag if prices actually different
                if old_p['price'] != new_p['price']:
                    difference = new_p['price'] - old_p['price']
                    percent_change = (difference / old_p['price']) * 100 if old_p['price'] > 0 else 0
                    
                    changes.append({
                        'item_number': item_number,
                        'item_description': new_p['item_description'] or old_p['item_description'],
                        'old_price': old_p['price'],
                        'new_price': new_p['price'],
                        'difference': difference,
                        'percent_change': percent_change,
                        'old_location': {
                            'table': old_p['table_index'],
                            'row': old_p['row_index'],
                            'col': old_p['col_index']
                        },
                        'new_location': {
                            'table': new_p['table_index'],
                            'row': new_p['row_index'],
                            'col': new_p['col_index']
                        },
                        'old_raw_text': old_p['raw_text'],
                        'new_raw_text': new_p['raw_text']
                    })
        
        return changes


# Example usage
if __name__ == "__main__":
    parser = PAPLParser()
    
    # Parse a PAPL document
    # result = parser.parse('PAPL_2024Q1.docx')
    
    # Export components
    # json_output = parser.export_to_json(result)
    # yaml_output = parser.export_to_yaml(result)
    # md_output = parser.export_to_markdown(result)
    
    print("PAPL Parser ready with price detection!")