from pdf2image import convert_from_path
import pytesseract
import pdfplumber
import re
import logging
from typing import Dict, List, Optional, Union, Tuple

logger = logging.getLogger(__name__)

def extract_text_with_ocr(pdf_path, page_num, multilingual=True):
    """
    Extract text from PDF page using OCR with multilingual support.
    
    Args:
        pdf_path: Path to the PDF file
        page_num: Page number (0-indexed)
        multilingual: Whether to use multilingual OCR settings
    
    Returns:
        str: Extracted text
    """
    try:
        images = convert_from_path(pdf_path, first_page=page_num+1, last_page=page_num+1, dpi=300)
        if not images:
            return ""
        
        image = images[0]
        
        if multilingual:
            # Try with multiple language configurations for better multilingual support
            language_configs = [
                'eng+chi_sim+chi_tra',  # English + Simplified & Traditional Chinese
                'eng+jpn',              # English + Japanese  
                'eng+kor',              # English + Korean
                'eng+chi_sim',          # English + Simplified Chinese
                'eng',                  # English only (fallback)
            ]
            
            best_text = ""
            max_length = 0
            
            for lang_config in language_configs:
                try:
                    # Custom OCR configuration for better accuracy
                    custom_config = r'--oem 3 --psm 6 -c tessedit_char_whitelist=0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz-/:()[]{}.,\n\r\t '
                    
                    if 'chi' in lang_config or 'jpn' in lang_config or 'kor' in lang_config:
                        # Remove character whitelist for CJK languages
                        custom_config = r'--oem 3 --psm 6'
                    
                    text = pytesseract.image_to_string(image, lang=lang_config, config=custom_config)
                    
                    # Select the result with the most content
                    if len(text.strip()) > max_length:
                        max_length = len(text.strip())
                        best_text = text
                        
                except Exception as e:
                    logger.debug(f"OCR failed with language config {lang_config}: {e}")
                    continue
            
            return best_text
        else:
            # Standard English-only OCR
            custom_config = r'--oem 3 --psm 6'
            return pytesseract.image_to_string(image, config=custom_config)
            
    except Exception as e:
        logger.error(f"OCR extraction failed for page {page_num} in {pdf_path}: {e}")
        return ""

def extract_tabular_data(pdf_path: str, page_num: int) -> Tuple[List[Dict[str, str]], str]:
    """
    Extract tabular data from a PDF page using pdfplumber.
    Also returns raw text for fallback pattern matching.
    
    Args:
        pdf_path: Path to the PDF file
        page_num: Page number (0-indexed)
    
    Returns:
        Tuple containing:
        - List of dictionaries with column headers as keys and cell values as values
        - Raw text from the page for fallback pattern matching
    """
    try:
        with pdfplumber.open(pdf_path) as pdf:
            page = pdf.pages[page_num]
            
            # Extract raw text for fallback
            raw_text = page.extract_text()
            
            # Extract tables from the page
            tables = page.extract_tables()
            if not tables:
                return [], raw_text
                
            # Process all tables found on the page
            results = []
            for table in tables:
                # Skip empty tables
                if not table or not any(table):
                    continue
                    
                # Try to find header row
                header_row = table[0]
                if not header_row or not any(header_row):
                    continue
                    
                # Clean and normalize headers
                headers = [str(h).strip() if h else f"column_{i}" 
                          for i, h in enumerate(header_row)]
                
                # Process each data row
                for row in table[1:]:
                    if not row or not any(row):
                        continue
                        
                    # Create dictionary mapping headers to cell values
                    row_dict = {}
                    for header, cell in zip(headers, row):
                        if cell:
                            row_dict[header] = str(cell).strip()
                    
                    if row_dict:  # Only add non-empty rows
                        results.append(row_dict)
            
            return results, raw_text
            
    except Exception as e:
        logger.error(f"Table extraction failed for page {page_num} in {pdf_path}: {e}")
        return [], ""

def extract_pattern_matches(text: str, pattern: str, match_type: str = "line_by_line") -> List[str]:
    """
    Extract all pattern matches from text using specified matching strategy.
    
    Args:
        text: Text to search for patterns
        pattern: Regular expression pattern
        match_type: Matching strategy - "line_by_line" or "global"
    
    Returns:
        List of matched values
    """
    matches = []
    try:
        if match_type == "line_by_line":
            # Split text into lines and search each line
            lines = text.split('\n')
            for line in lines:
                line_matches = re.finditer(pattern, line)
                for match in line_matches:
                    if match.groups():
                        matches.append(match.group(1))  # Capture first group
                    else:
                        matches.append(match.group(0))  # Or full match
        else:  # global matching
            # Search entire text at once
            text_matches = re.finditer(pattern, text)
            for match in text_matches:
                if match.groups():
                    matches.append(match.group(1))
                else:
                    matches.append(match.group(0))
                    
    except Exception as e:
        logger.error(f"Pattern matching failed for pattern {pattern}: {e}")
    
    return list(set(matches))  # Remove duplicates
