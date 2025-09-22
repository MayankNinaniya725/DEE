#!/usr/bin/env python3
"""
Simulate Hengrun extraction with poor OCR quality text to test fallback.
"""

import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'extractor_project.settings')
django.setup()

from extractor.utils.config_loader import load_vendor_config
from extractor.utils.pattern_extractor import extract_patterns_from_text
import json

def simulate_hengrun_extraction():
    print("🧪 Simulating Hengrun Extraction - Poor OCR Quality")
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
    
    # Simulate poor OCR text - only certificate number visible
    poor_ocr_text = """
    Some garbled OCR text...
    Certificate No.: HR20230608013
    Test Report...
    More garbled text...
    """
    
    print(f"\n📄 Simulated OCR text ({len(poor_ocr_text)} characters):")
    print(f"   {repr(poor_ocr_text)}")
    
    # Test pattern extraction with poor OCR
    print(f"\n🎯 Running pattern extraction with poor OCR...")
    entries = extract_patterns_from_text(poor_ocr_text, config)
    
    print(f"\n📊 EXTRACTION RESULTS:")
    print(f"   Entries found: {len(entries)}")
    
    for i, entry in enumerate(entries, 1):
        print(f"\n   📋 Entry {i}:")
        for key, value in entry.items():
            if key == "extraction_quality":
                print(f"      🔍 {key}: {value}")
            else:
                print(f"      {key}: {value}")
    
    # Test with empty/no text (worst case)
    print(f"\n" + "="*60)
    print(f"🔬 Testing with completely empty OCR (worst case):")
    
    empty_entries = extract_patterns_from_text("", config)
    print(f"   Entries found: {len(empty_entries)}")
    
    for i, entry in enumerate(empty_entries, 1):
        print(f"\n   📋 Entry {i}:")
        for key, value in entry.items():
            if key == "extraction_quality":
                print(f"      🔍 {key}: {value}")
            else:
                print(f"      {key}: {value}")

if __name__ == "__main__":
    simulate_hengrun_extraction()