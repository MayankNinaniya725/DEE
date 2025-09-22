"""
Advanced Table Parser for POSCO Steel Certificates
Handles complex table layouts with multi-line rows, misaligned cells, and vertical alignment
"""

import re
import logging
import pdfplumber
from typing import Dict, List, Tuple, Any, Optional
import pandas as pd
from collections import defaultdict

logger = logging.getLogger(__name__)

class PoscoTableParser:
    """Advanced parser for POSCO table structures"""
    
    def __init__(self):
        self.plate_patterns = [
            r'\b(PP\d{5,6}(?:-\d{2,4})?(?:-\d{4})?)\b',
            r'\b(PP\d{5,6}[A-Z]\d{1,4})\b',
            r'\b(\d{2}[A-Z]{2}\d{4}[A-Z]\d{1,4})\b'
        ]
        
        self.heat_patterns = [
            r'\b(SU\d{5,8})\b',
            r'\b([A-Z]{1,3}\d{5,8})\b',
            r'\b(\d{6,8}[A-Z]{0,2})\b'
        ]
        
        self.cert_patterns = [
            r'\b(\d{6}-FP\d{2}[A-Z0-9]+-[0-9A-Z\-]+)\b',
            r'Certificate\s+No[.\s]*(\d{6}-[A-Z0-9\-]+)',
            r'(\d{6}-FP[0-9A-Z\-]+)'
        ]
    
    def extract_posco_data(self, pdf_path: str) -> List[Dict[str, Any]]:
        """
        Main extraction method for POSCO certificates
        Handles complex table layouts with vertical alignment
        """
        results = []
        
        try:
            with pdfplumber.open(pdf_path) as pdf:
                # First, extract certificate number from header (shared across all entries)
                cert_no = self._extract_certificate_number(pdf)
                
                for page_num, page in enumerate(pdf.pages):
                    logger.info(f"Processing page {page_num + 1}")
                    
                    # Extract table data using multiple strategies
                    page_data = self._extract_page_data(page, page_num)
                    
                    # Process and align data
                    aligned_data = self._align_plate_heat_data(page_data, page_num)
                    
                    # Add certificate number to each entry
                    for entry in aligned_data:
                        entry['TEST_CERT_NO'] = cert_no or 'N/A'
                        entry['page_number'] = page_num + 1
                        results.append(entry)
                        
        except Exception as e:
            logger.error(f"Error extracting POSCO data: {e}")
            
        return results
    
    def _extract_certificate_number(self, pdf) -> Optional[str]:
        """Extract certificate number from document header"""
        cert_no = None
        
        try:
            # Check first few pages for certificate number
            for page in pdf.pages[:3]:
                text = page.extract_text() or ""
                
                for pattern in self.cert_patterns:
                    match = re.search(pattern, text, re.IGNORECASE)
                    if match:
                        cert_no = match.group(1).strip()
                        logger.info(f"Found certificate number: {cert_no}")
                        return cert_no
                        
        except Exception as e:
            logger.error(f"Error extracting certificate number: {e}")
            
        return cert_no
    
    def _extract_page_data(self, page, page_num: int) -> Dict[str, List]:
        """
        Extract all potential plate and heat numbers from a page
        Uses multiple extraction strategies
        """
        page_data = {
            'plates': [],
            'heats': [],
            'text_blocks': [],
            'tables': []
        }
        
        try:
            # Strategy 1: Extract from structured tables
            tables = page.extract_tables()
            if tables:
                page_data['tables'] = tables
                self._extract_from_tables(tables, page_data)
            
            # Strategy 2: Extract from raw text with position information
            text = page.extract_text() or ""
            self._extract_from_text(text, page_data)
            
            # Strategy 3: Extract from text with coordinates (if available)
            try:
                chars = page.chars
                self._extract_from_positioned_text(chars, page_data)
            except:
                pass  # Fallback if char extraction fails
                
        except Exception as e:
            logger.error(f"Error extracting data from page {page_num}: {e}")
            
        return page_data
    
    def _extract_from_tables(self, tables: List, page_data: Dict):
        """Extract data from structured tables"""
        for table in tables:
            if not table or len(table) < 2:
                continue
                
            # Find header row and identify columns
            header_indices = self._find_table_columns(table[0])
            
            # Process data rows
            for row_idx, row in enumerate(table[1:], 1):
                if not row or len(row) < 2:
                    continue
                    
                # Extract plate numbers
                if 'product_col' in header_indices:
                    col_idx = header_indices['product_col']
                    if col_idx < len(row) and row[col_idx]:
                        cell_value = str(row[col_idx]).strip()
                        plates = self._find_plates_in_text(cell_value)
                        for plate in plates:
                            page_data['plates'].append({
                                'value': plate,
                                'source': 'table',
                                'row': row_idx,
                                'confidence': 0.9
                            })
                
                # Extract heat numbers
                if 'heat_col' in header_indices:
                    col_idx = header_indices['heat_col']
                    if col_idx < len(row) and row[col_idx]:
                        cell_value = str(row[col_idx]).strip()
                        heats = self._find_heats_in_text(cell_value)
                        for heat in heats:
                            page_data['heats'].append({
                                'value': heat,
                                'source': 'table',
                                'row': row_idx,
                                'confidence': 0.9
                            })
    
    def _extract_from_text(self, text: str, page_data: Dict):
        """Extract data from raw text"""
        lines = text.split('\n')
        
        for line_idx, line in enumerate(lines):
            if not line.strip():
                continue
                
            # Extract plates from this line
            plates = self._find_plates_in_text(line)
            for plate in plates:
                page_data['plates'].append({
                    'value': plate,
                    'source': 'text',
                    'line': line_idx,
                    'confidence': 0.7
                })
            
            # Extract heats from this line
            heats = self._find_heats_in_text(line)
            for heat in heats:
                page_data['heats'].append({
                    'value': heat,
                    'source': 'text',
                    'line': line_idx,
                    'confidence': 0.7
                })
    
    def _extract_from_positioned_text(self, chars: List, page_data: Dict):
        """Extract data using character positions for better alignment"""
        # Group characters by approximate vertical position
        lines_by_y = defaultdict(list)
        
        for char in chars:
            if char.get('text', '').strip():
                y_pos = round(char.get('y0', 0), 1)  # Round to avoid too many groups
                lines_by_y[y_pos].append(char)
        
        # Process each line
        for y_pos, line_chars in lines_by_y.items():
            # Sort by x position
            line_chars.sort(key=lambda c: c.get('x0', 0))
            
            # Reconstruct line text
            line_text = ''.join(c.get('text', '') for c in line_chars)
            
            # Extract plates and heats with position info
            plates = self._find_plates_in_text(line_text)
            for plate in plates:
                page_data['plates'].append({
                    'value': plate,
                    'source': 'positioned',
                    'y_pos': y_pos,
                    'confidence': 0.8
                })
            
            heats = self._find_heats_in_text(line_text)
            for heat in heats:
                page_data['heats'].append({
                    'value': heat,
                    'source': 'positioned',
                    'y_pos': y_pos,
                    'confidence': 0.8
                })
    
    def _find_table_columns(self, header_row: List) -> Dict[str, int]:
        """Identify relevant columns in table header"""
        indices = {}
        
        for idx, header in enumerate(header_row):
            if not header:
                continue
                
            header_str = str(header).lower().strip()
            
            if any(term in header_str for term in ['product', 'part', 'plate']):
                indices['product_col'] = idx
            elif any(term in header_str for term in ['heat', 'lot']):
                indices['heat_col'] = idx
            elif any(term in header_str for term in ['size', 'dimension']):
                indices['size_col'] = idx
                
        return indices
    
    def _find_plates_in_text(self, text: str) -> List[str]:
        """Find all plate numbers in text using multiple patterns"""
        plates = []
        
        for pattern in self.plate_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            plates.extend(matches)
            
        return list(set(plates))  # Remove duplicates
    
    def _find_heats_in_text(self, text: str) -> List[str]:
        """Find all heat numbers in text using multiple patterns"""
        heats = []
        
        for pattern in self.heat_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            heats.extend(matches)
            
        return list(set(heats))  # Remove duplicates
    
    def _align_plate_heat_data(self, page_data: Dict, page_num: int) -> List[Dict[str, str]]:
        """
        Align plate numbers with heat numbers based on vertical position
        This handles the complex POSCO table layouts where data spans multiple lines
        """
        aligned_entries = []
        
        # Get unique plates and heats sorted by confidence
        plates = sorted(page_data['plates'], key=lambda x: x['confidence'], reverse=True)
        heats = sorted(page_data['heats'], key=lambda x: x['confidence'], reverse=True)
        
        if not plates:
            logger.warning(f"No plate numbers found on page {page_num}")
            return []
        
        if not heats:
            logger.warning(f"No heat numbers found on page {page_num}")
            # Still create entries with plates only
            for plate in plates[:10]:  # Limit to prevent spam
                aligned_entries.append({
                    'PLATE_NO': plate['value'],
                    'HEAT_NO': 'N/A'
                })
            return aligned_entries
        
        # Strategy 1: Try to match by table row if available
        table_matches = self._match_by_table_row(plates, heats)
        aligned_entries.extend(table_matches)
        
        # Strategy 2: Match by vertical position (for positioned text)
        position_matches = self._match_by_position(plates, heats)
        aligned_entries.extend(position_matches)
        
        # Strategy 3: Sequential pairing (fallback)
        if not aligned_entries:
            sequential_matches = self._match_sequentially(plates, heats)
            aligned_entries.extend(sequential_matches)
        
        # Remove duplicates and validate
        unique_entries = []
        seen_combinations = set()
        
        for entry in aligned_entries:
            combination = (entry['PLATE_NO'], entry['HEAT_NO'])
            if combination not in seen_combinations:
                seen_combinations.add(combination)
                unique_entries.append(entry)
        
        logger.info(f"Page {page_num}: Found {len(unique_entries)} aligned plate-heat combinations")
        return unique_entries[:20]  # Limit to reasonable number
    
    def _match_by_table_row(self, plates: List, heats: List) -> List[Dict[str, str]]:
        """Match plates and heats by table row number"""
        matches = []
        
        # Group by source and row
        plate_by_row = defaultdict(list)
        heat_by_row = defaultdict(list)
        
        for plate in plates:
            if plate['source'] == 'table' and 'row' in plate:
                plate_by_row[plate['row']].append(plate)
        
        for heat in heats:
            if heat['source'] == 'table' and 'row' in heat:
                heat_by_row[heat['row']].append(heat)
        
        # Match by row number
        for row_num in plate_by_row.keys():
            if row_num in heat_by_row:
                for plate in plate_by_row[row_num]:
                    for heat in heat_by_row[row_num]:
                        matches.append({
                            'PLATE_NO': plate['value'],
                            'HEAT_NO': heat['value']
                        })
        
        return matches
    
    def _match_by_position(self, plates: List, heats: List) -> List[Dict[str, str]]:
        """Match plates and heats by vertical position"""
        matches = []
        
        # Get positioned items
        positioned_plates = [p for p in plates if 'y_pos' in p]
        positioned_heats = [h for h in heats if 'y_pos' in h]
        
        if not positioned_plates or not positioned_heats:
            return matches
        
        # Match by proximity in y-position (within tolerance)
        tolerance = 5.0  # Allow some variation in vertical position
        
        for plate in positioned_plates:
            plate_y = plate['y_pos']
            best_heat = None
            min_distance = float('inf')
            
            for heat in positioned_heats:
                heat_y = heat['y_pos']
                distance = abs(plate_y - heat_y)
                
                if distance <= tolerance and distance < min_distance:
                    min_distance = distance
                    best_heat = heat
            
            if best_heat:
                matches.append({
                    'PLATE_NO': plate['value'],
                    'HEAT_NO': best_heat['value']
                })
        
        return matches
    
    def _match_sequentially(self, plates: List, heats: List) -> List[Dict[str, str]]:
        """Sequential matching as fallback"""
        matches = []
        
        # Get unique values
        unique_plates = list({p['value'] for p in plates})
        unique_heats = list({h['value'] for h in heats})
        
        # Pair them up sequentially
        min_count = min(len(unique_plates), len(unique_heats))
        
        for i in range(min_count):
            matches.append({
                'PLATE_NO': unique_plates[i],
                'HEAT_NO': unique_heats[i]
            })
        
        # Handle remaining plates without heats
        for i in range(min_count, len(unique_plates)):
            matches.append({
                'PLATE_NO': unique_plates[i],
                'HEAT_NO': 'N/A'
            })
        
        return matches

def extract_posco_table_data(pdf_path: str) -> List[Dict[str, Any]]:
    """
    Convenience function for POSCO table extraction
    """
    parser = PoscoTableParser()
    return parser.extract_posco_data(pdf_path)