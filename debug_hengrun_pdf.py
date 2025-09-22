#!/usr/bin/env python3
"""
Debug Hengrun PDF extraction to identify why patterns are failing
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
import re

def debug_hengrun_pdf():
    """Debug the specific Hengrun PDF extraction"""
    
    pdf_path = "media/hengrun_test.pdf"
    config_path = "extractor/vendor_configs/hengrum_steel.json"
    
    if not os.path.exists(pdf_path):
        print(f"❌ PDF not found: {pdf_path}")
        return
    
    print(f"🔍 Debugging Hengrun PDF: {pdf_path}")
    print("=" * 60)
    
    # 1. Load config
    vendor_config = load_vendor_config(config_path)
    if not vendor_config:
        print("❌ Failed to load Hengrun config")
        return
        
    print(f"✅ Loaded config: {vendor_config.get('vendor_name')}")
    
    patterns = vendor_config.get('fields', {})
    for field, config in patterns.items():
        pattern = config.get('pattern', '')
        print(f"  {field}: {pattern}")
    
    # 2. Extract raw text and OCR from PDF
    print(f"\n📄 PDF Content Analysis:")
    
    try:
        # Try pdfplumber first
        with pdfplumber.open(pdf_path) as pdf:
            print(f"  Total pages: {len(pdf.pages)}")
            
            for page_num, page in enumerate(pdf.pages):
                text = page.extract_text()
                print(f"\n📑 Page {page_num + 1} (pdfplumber):")
                print(f"  Text length: {len(text) if text else 0} characters")
                
                if text and len(text) > 0:
                    print(f"  Sample text (first 500 chars):")
                    print(f"  {text[:500]}")
                else:
                    print(f"  ❌ No text extracted by pdfplumber")
        
        # Try OCR extraction
        print(f"\n🔍 OCR Text Analysis:")
        from extractor.utils.ocr_helper import extract_text_with_ocr
        ocr_text = extract_text_with_ocr(pdf_path, 0)
        
        if ocr_text:
            print(f"  OCR text length: {len(ocr_text)} characters")
            print(f"\n📝 Full OCR Text:")
            print("-" * 40)
            print(ocr_text)
            print("-" * 40)
            
            # Test patterns against OCR text
            print(f"\n🧪 Pattern Testing Against OCR Text:")
            
            lines = ocr_text.split('\n')
            print(f"  Total lines: {len(lines)}")
            
            for field_name, field_config in patterns.items():
                pattern = field_config.get('pattern', '')
                print(f"\n📋 Testing {field_name}:")
                print(f"  Pattern: {pattern}")
                
                matches = []
                matching_lines = []
                
                for i, line in enumerate(lines):
                    line_matches = re.findall(pattern, line, re.IGNORECASE)
                    if line_matches:
                        matches.extend(line_matches)
                        matching_lines.append((i+1, line.strip(), line_matches))
                
                if matches:
                    print(f"  ✅ Found {len(matches)} matches:")
                    for line_num, line_text, line_matches in matching_lines:
                        print(f"    Line {line_num}: {line_text}")
                        print(f"      Matches: {line_matches}")
                else:
                    print(f"  ❌ No matches found")
                    
                    # Suggest what might be in the text
                    if field_name == "PLATE_NO":
                        potential_plates = []
                        for line in lines:
                            # Look for number-number patterns
                            potential = re.findall(r'\b(\d+[-‐]\d+)\b', line)
                            if potential:
                                potential_plates.extend(potential)
                        if potential_plates:
                            print(f"  💡 Potential plate patterns found: {potential_plates}")
                    
                    elif field_name == "HEAT_NO":
                        potential_heats = []
                        for line in lines:
                            # Look for S followed by numbers/letters
                            potential = re.findall(r'\b(S[A-Z0-9]+)\b', line)
                            if potential:
                                potential_heats.extend(potential)
                        if potential_heats:
                            print(f"  💡 Potential heat patterns found: {potential_heats}")
                    
                    elif field_name == "TEST_CERT_NO":
                        potential_certs = []
                        for line in lines:
                            # Look for various certificate patterns
                            potential = re.findall(r'\b([A-Z]{2}[0-9]{8,})\b|\b([0-9]{4}-[0-9]{4}-[0-9]{3})\b', line)
                            if potential:
                                for groups in potential:
                                    for group in groups:
                                        if group:
                                            potential_certs.append(group)
                        if potential_certs:
                            print(f"  💡 Potential certificate patterns found: {potential_certs}")
        
        else:
            print(f"  ❌ No OCR text extracted")
    
    except Exception as e:
        print(f"❌ Error analyzing PDF: {e}")
        import traceback
        traceback.print_exc()
    
    # 3. Run actual extraction and see results
    print(f"\n🚀 Running Actual Extraction:")
    try:
        results, stats = extract_pdf_fields(pdf_path, vendor_config)
        
        print(f"\n📊 Extraction Results:")
        print(f"  Total entries: {len(results)}")
        print(f"  Pages processed: {stats['successful_pages']}/{stats['total_pages']}")
        print(f"  Failed pages: {stats.get('failed_pages', [])}")
        print(f"  OCR fallback: {stats.get('ocr_fallback_pages', [])}")
        
        if results:
            print(f"\n📝 Extracted entries:")
            for i, entry in enumerate(results):
                print(f"\n  Entry {i+1}:")
                for key, value in entry.items():
                    if key in ['PLATE_NO', 'HEAT_NO', 'TEST_CERT_NO', 'Vendor', 'Page']:
                        print(f"    {key}: {value}")
        else:
            print(f"❌ No entries extracted!")
            
    except Exception as e:
        print(f"❌ Extraction failed: {e}")
        import traceback
        traceback.print_exc()
    
    # 4. Recommendations
    print(f"\n💡 Recommendations:")
    print(f"  1. If patterns found potential matches, update regex patterns")
    print(f"  2. If OCR quality is poor, consider document preprocessing")
    print(f"  3. Check if certificate format differs from expected pattern")
    print(f"  Expected: 2 entries with plate numbers 6-0003 and 6-0002")

if __name__ == "__main__":
    debug_hengrun_pdf()