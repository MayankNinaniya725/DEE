#!/usr/bin/env python3
"""
Debug POSCO extraction to identify why only single entry is found
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

from extractor.utils.extractor import extract_pdf_fields
from extractor.utils.config_loader import load_vendor_config
import pdfplumber

def debug_posco_extraction():
    """Debug POSCO extraction step by step"""
    
    pdf_path = "media/posco_test.pdf"
    config_path = "extractor/vendor_configs/posco_steel.json"
    
    if not os.path.exists(pdf_path):
        print(f"❌ PDF not found: {pdf_path}")
        return
    
    print(f"🔍 Debugging POSCO extraction for: {pdf_path}")
    print("=" * 60)
    
    # 1. Load config
    vendor_config = load_vendor_config(config_path)
    if not vendor_config:
        print("❌ Failed to load POSCO config")
        return
        
    print(f"✅ Loaded config: {vendor_config.get('vendor_name')}")
    
    # 2. Extract raw text from PDF
    print("\n📄 Analyzing PDF content:")
    with pdfplumber.open(pdf_path) as pdf:
        print(f"  Total pages: {len(pdf.pages)}")
        
        for page_num, page in enumerate(pdf.pages):
            text = page.extract_text()
            print(f"\n📑 Page {page_num + 1}:")
            print(f"  Text length: {len(text) if text else 0} characters")
            
            if text:
                # Look for key patterns
                lines = text.split('\n')
                print(f"  Total lines: {len(lines)}")
                
                # Check for heat numbers
                heat_numbers = []
                plate_numbers = []
                cert_numbers = []
                
                for line in lines:
                    if 'SU' in line and any(c.isdigit() for c in line):
                        heat_numbers.append(line.strip())
                    if any(keyword in line.upper() for keyword in ['PLATE', 'NO']):
                        plate_numbers.append(line.strip())
                    if any(keyword in line.upper() for keyword in ['CERT', 'TEST']):
                        cert_numbers.append(line.strip())
                
                print(f"  Lines with 'SU' + digits: {len(heat_numbers)}")
                if heat_numbers:
                    for i, heat in enumerate(heat_numbers[:5]):  # Show first 5
                        print(f"    {i+1}: {heat}")
                
                print(f"  Lines with 'PLATE/NO': {len(plate_numbers)}")
                print(f"  Lines with 'CERT/TEST': {len(cert_numbers)}")
                
                # Show sample of first 10 lines
                print(f"\n  Sample lines (first 10):")
                for i, line in enumerate(lines[:10]):
                    print(f"    {i+1:2d}: {line.strip()}")
    
    # 3. Test pattern extraction
    print(f"\n🔍 Testing pattern extraction:")
    patterns = vendor_config.get('fields', {})
    
    for field_name, field_config in patterns.items():
        pattern = field_config.get('pattern', '')
        print(f"  {field_name}: {pattern}")
    
    # 4. Run actual extraction
    print(f"\n🚀 Running extraction:")
    try:
        results, stats = extract_pdf_fields(pdf_path, vendor_config)
        
        print(f"\n📊 Extraction Results:")
        print(f"  Total entries: {len(results)}")
        print(f"  Pages processed: {stats['successful_pages']}/{stats['total_pages']}")
        print(f"  Failed pages: {stats.get('failed_pages', [])}")
        print(f"  OCR fallback: {stats.get('ocr_fallback_pages', [])}")
        print(f"  Preprocessing applied: {stats.get('preprocessing_applied', False)}")
        
        if results:
            print(f"\n📝 Extracted entries:")
            for i, entry in enumerate(results):
                print(f"\n  Entry {i+1}:")
                for key, value in entry.items():
                    if key in ['PLATE_NO', 'HEAT_NO', 'TEST_CERT_NO', '_corrections_applied']:
                        print(f"    {key}: {value}")
        else:
            print(f"❌ No entries extracted!")
            
    except Exception as e:
        print(f"❌ Extraction failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_posco_extraction()