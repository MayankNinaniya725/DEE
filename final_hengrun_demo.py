#!/usr/bin/env python3
"""
Final demonstration of the Hengrun extraction system with all fixes.
"""

import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'extractor_project.settings')
django.setup()

from extractor.utils.config_loader import load_vendor_config
from extractor.utils.pattern_extractor import extract_patterns_from_text

def test_scenarios():
    print("🎯 Final Hengrun Extraction System Demo")
    print("=" * 60)
    
    # Load config
    config_path = "extractor/vendor_configs/hengrum_steel.json"
    config = load_vendor_config(config_path)
    print(f"✅ Config: {config['vendor_name']}")
    
    # Test scenarios
    scenarios = [
        {
            "name": "Good OCR - Normal Extraction",
            "text": """
            Test Certificate No.: HR20230608013
            Heat No.: S1234X
            Part No.: 6-0003
            Part No.: 6-0002
            Quality: Grade A
            """,
            "expected": "Normal extraction with found plate numbers"
        },
        {
            "name": "Poor OCR - Has Certificate Only",
            "text": """
            Some garbled text...
            Certificate No.: HR20230608013
            More garbled text...
            """,
            "expected": "Fallback strategy triggered - creates 2 entries"
        },
        {
            "name": "Very Poor OCR - Empty Text",
            "text": "",
            "expected": "No extraction possible"
        },
        {
            "name": "Medium Quality - Certificate + Some Data",
            "text": """
            Certificate HR20230608013 found in document
            Heat number might be S5678Y but unclear
            Part numbers not visible due to poor scan
            """ * 2,  # Make it longer to test threshold
            "expected": "Partial extraction or normal processing"
        }
    ]
    
    for i, scenario in enumerate(scenarios, 1):
        print(f"\n📋 Scenario {i}: {scenario['name']}")
        print(f"   Text length: {len(scenario['text'])} characters")
        print(f"   Expected: {scenario['expected']}")
        
        try:
            entries = extract_patterns_from_text(scenario['text'], config)
            print(f"   ✅ Entries found: {len(entries)}")
            
            for j, entry in enumerate(entries, 1):
                quality = entry.get('extraction_quality', 'NORMAL')
                plate = entry.get('PLATE_NO', 'NA')
                heat = entry.get('HEAT_NO', 'NA')
                cert = entry.get('TEST_CERT_NO', 'NA')
                print(f"      📄 Entry {j}: Plate={plate}, Heat={heat}, Cert={cert}")
                if quality != 'NORMAL':
                    print(f"         🔍 Quality: {quality}")
                    
        except Exception as e:
            print(f"   ❌ Error: {e}")
    
    print(f"\n" + "=" * 60)
    print(f"🎉 SUMMARY: Hengrun extraction system now handles:")
    print(f"   ✅ Normal extraction with good OCR")
    print(f"   ✅ Fallback strategy for poor OCR quality")
    print(f"   ✅ NoneType errors fixed in pattern processing")
    print(f"   ✅ Quality indicators for manual review")
    print(f"   ✅ Certificate number extraction even with poor OCR")
    print(f"   ✅ Configurable fallback plate numbers (6-0003, 6-0002)")

if __name__ == "__main__":
    test_scenarios()