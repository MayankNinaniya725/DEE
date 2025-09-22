#!/usr/bin/env python3
"""
Deep analysis of POSCO PDF structure and content
"""
import os
import sys
import django
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Configure Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'extractor_project.settings')
django.setup()

import pdfplumber
from PyPDF2 import PdfReader

def analyze_posco_pdf_deeply():
    """Deep analysis of the POSCO PDF structure"""
    
    pdf_path = "media/posco_test.pdf"
    
    if not os.path.exists(pdf_path):
        print(f"❌ PDF not found: {pdf_path}")
        return
    
    print(f"🔍 Deep PDF Analysis: {pdf_path}")
    print("=" * 60)
    
    # 1. Try different PDF libraries
    print("1️⃣  Testing different PDF extraction methods:")
    
    # Method 1: pdfplumber
    print(f"\n📖 pdfplumber extraction:")
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page_num, page in enumerate(pdf.pages):
                text = page.extract_text()
                print(f"  Page {page_num + 1}: {len(text) if text else 0} characters")
                if text and len(text) > 0:
                    print(f"    Sample: {text[:200]}")
                
                # Try table extraction
                tables = page.extract_tables()
                print(f"  Tables found: {len(tables)}")
                
                if tables:
                    for i, table in enumerate(tables):
                        print(f"    Table {i+1}: {len(table)} rows")
                        if table:
                            print(f"    Sample row: {table[0] if table else 'None'}")
                            
    except Exception as e:
        print(f"  ❌ pdfplumber failed: {e}")
    
    # Method 2: PyPDF2
    print(f"\n📖 PyPDF2 extraction:")
    try:
        reader = PdfReader(pdf_path)
        for page_num, page in enumerate(reader.pages):
            text = page.extract_text()
            print(f"  Page {page_num + 1}: {len(text) if text else 0} characters")
            if text and len(text) > 0:
                print(f"    Sample: {text[:200]}")
    except Exception as e:
        print(f"  ❌ PyPDF2 failed: {e}")
    
    # Skip PyMuPDF as it's not installed
    print(f"\n📖 PyMuPDF: Not available (requires installation)")
    
    # 4. Test OCR extraction
    print(f"\n🔍 OCR Analysis:")
    try:
        from extractor.utils.ocr_helper import extract_text_with_ocr
        ocr_text = extract_text_with_ocr(pdf_path, 0)  # Page 0
        print(f"  OCR text length: {len(ocr_text) if ocr_text else 0} characters")
        
        if ocr_text:
            lines = ocr_text.split('\n')
            print(f"  OCR lines: {len(lines)}")
            
            # Look for patterns in OCR text
            su_matches = []
            pp_matches = []
            cert_matches = []
            
            import re
            
            for line in lines:
                # Look for heat numbers
                if re.search(r'SU\d+', line):
                    su_matches.append(line.strip())
                # Look for plate numbers  
                if re.search(r'PP\d+', line):
                    pp_matches.append(line.strip())
                # Look for certificates
                if re.search(r'Certificate|CERT', line, re.IGNORECASE):
                    cert_matches.append(line.strip())
            
            print(f"  OCR Heat numbers found: {len(su_matches)}")
            for i, match in enumerate(su_matches[:5]):
                print(f"    {i+1}: {match}")
                
            print(f"  OCR Plate numbers found: {len(pp_matches)}")
            for i, match in enumerate(pp_matches[:5]):
                print(f"    {i+1}: {match}")
                
            print(f"  OCR Certificates found: {len(cert_matches)}")
            for i, match in enumerate(cert_matches[:3]):
                print(f"    {i+1}: {match}")
                
    except Exception as e:
        print(f"  ❌ OCR failed: {e}")
    
    # 5. Test specialized POSCO parser
    print(f"\n🔧 Testing POSCO Specialized Parser:")
    try:
        from extractor.utils.posco_table_parser import extract_posco_table_data
        posco_results = extract_posco_table_data(pdf_path)
        
        print(f"  POSCO parser results: {len(posco_results) if posco_results else 0} entries")
        if posco_results:
            for i, result in enumerate(posco_results[:3]):
                print(f"    Entry {i+1}: {result}")
                
    except Exception as e:
        print(f"  ❌ POSCO parser failed: {e}")

if __name__ == "__main__":
    analyze_posco_pdf_deeply()