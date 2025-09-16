import pdfplumber
import pandas as pd
import re
import logging
from typing import List, Dict, Any, Tuple, Optional

logger = logging.getLogger(__name__)

def extract_tables_from_page(page: Any, vendor_config: Dict[str, Any]) -> List[Dict[str, str]]:
    """
    Extract tables from a PDF page using pdfplumber and match against field patterns.
    
    Args:
        page: pdfplumber page object
        vendor_config: Vendor configuration dictionary
    
    Returns:
        List of extracted entries
    """
    entries = []
    try:
        # Extract tables from the page
        tables = page.extract_tables()
        if not tables:
            return []
        
        fields = vendor_config["fields"]
        
        for table in tables:
            if not table or len(table) < 2:  # Need at least header + 1 data row
                continue
            
            # Try to identify column indices for our fields
            header_row = table[0]
            field_columns = {}
            
            # Map field names to column indices
            for field_name, field_info in fields.items():
                column_name = field_info.get("table_column", "") if isinstance(field_info, dict) else ""
                pattern = field_info.get("pattern", "") if isinstance(field_info, dict) else field_info
                
                for idx, header in enumerate(header_row):
                    if not header:
                        continue
                    header = str(header).strip()
                    
                    # Try exact match first
                    if column_name and column_name.lower() in header.lower():
                        field_columns[field_name] = idx
                        break
                    
                    # Try pattern match
                    if re.search(pattern, header, re.IGNORECASE):
                        field_columns[field_name] = idx
                        break
            
            # Process data rows
            for row in table[1:]:
                if not any(row):  # Skip empty rows
                    continue
                
                entry = {
                    "PLATE_NO": "NA",
                    "HEAT_NO": "NA",
                    "TEST_CERT_NO": "NA"
                }
                
                # Extract values from identified columns
                for field_name, col_idx in field_columns.items():
                    if col_idx < len(row) and row[col_idx]:
                        value = str(row[col_idx]).strip()
                        
                        # Apply pattern matching if needed
                        field_info = fields[field_name]
                        if isinstance(field_info, dict):
                            pattern = field_info["pattern"]
                            match = re.search(pattern, value, re.IGNORECASE)
                            if match:
                                value = match.group(1) if match.lastindex else match.group(0)
                        
                        # Normalize field names
                        if field_name in ["PART_NO", "PRODUCT_NO"]:
                            entry["PLATE_NO"] = value
                        elif field_name in ["CERTIFICATE_NO", "REPORT_NO"]:
                            entry["TEST_CERT_NO"] = value
                        else:
                            entry[field_name] = value
                
                # Only add entry if we have at least one valid value
                if any(v != "NA" for v in entry.values()):
                    entries.append(entry)
    
    except Exception as e:
        logger.error(f"Table extraction failed: {e}")
        return []
    
    return entries

def extract_text_from_page(page: Any) -> str:
    """Extract text from a page with preprocessing."""
    try:
        text = page.extract_text()
        if text:
            # Clean up the text
            text = re.sub(r'\s+', ' ', text)  # Normalize whitespace
            text = text.replace('\u200b', '')  # Remove zero-width spaces
            return text.strip()
    except Exception as e:
        logger.error(f"Text extraction failed: {e}")
    return ""