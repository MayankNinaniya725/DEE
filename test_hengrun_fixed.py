#!/usr/bin/env python3
"""
Test Hengrun extraction system with the fixes for NoneType error and fallback strategy.
"""

import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'extractor_project.settings')
django.setup()

from extractor.utils.config_loader import load_vendor_config
from extractor.utils.pattern_extractor import extract_patterns_from_text
import pdfplumber
import json

def test_hengrun_extraction():
    print("🧪 Testing Hengrun Extraction System with Fixes")
    print("=" * 60)
    
    # Load Hengrun config
    try:
        config_path = "extractor/vendor_configs/hengrum_steel.json"
        config = load_vendor_config(config_path)
        print(f"✅ Loaded config for: {config['vendor_name']}")
        print(f"📋 Fallback enabled: {config.get('fallback_strategy', {}).get('enabled', False)}")
    except Exception as e:
        print(f"❌ Error loading config: {e}")
        return
    
    # Test with the actual PDF
    pdf_path = "media/uploaded_files/test_hengrun.pdf"
    
    if not os.path.exists(pdf_path):
        print(f"⚠️  PDF not found at: {pdf_path}")
        print("Please ensure the PDF is uploaded first.")
        return
    
    try:
        print(f"\n🔍 Extracting text from: {pdf_path}")
        
        # Extract text using pdfplumber
        text = ""
        try:
            with pdfplumber.open(pdf_path) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"
        except Exception as e:
            print(f"Error extracting with pdfplumber: {e}")
            text = ""
        text_length = len(text) if text else 0
        print(f"📄 Text extracted: {text_length} characters")
        
        if text_length > 0:
            print(f"📝 First 200 characters:")
            print(f"   {repr(text[:200])}")
        
        # Try pattern extraction
        print(f"\n🎯 Running pattern extraction...")
        entries = extract_patterns_from_text(text or "", config)
        
        print(f"\n📊 EXTRACTION RESULTS:")
        print(f"   Entries found: {len(entries)}")
        
        for i, entry in enumerate(entries, 1):
            print(f"\n   📋 Entry {i}:")
            for key, value in entry.items():
                print(f"      {key}: {value}")
        
        # Check extraction quality
        if entries:
            has_quality_flag = any('extraction_quality' in entry for entry in entries)
            if has_quality_flag:
                print(f"\n⚠️  QUALITY STATUS: Fallback strategy was used due to poor OCR")
            else:
                print(f"\n✅ QUALITY STATUS: Normal extraction successful")
        else:
            print(f"\n❌ EXTRACTION STATUS: No entries found")
            
        # Test certificate number extraction specifically
        cert_pattern = config['fields']['TEST_CERT_NO']['pattern']
        import re
        cert_matches = re.findall(cert_pattern, text or "", re.IGNORECASE)
        print(f"\n🎫 Certificate matches found: {cert_matches}")
        
    except Exception as e:
        print(f"❌ Error during extraction: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_hengrun_extraction()