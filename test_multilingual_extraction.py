#!/usr/bin/env python3
"""
Test script to demonstrate the enhanced multilingual PDF extraction capabilities.

This script shows how the enhanced extractor handles:
1. Standard single-language PDFs (preserved existing functionality)
2. Multilingual PDFs with Chinese/English mixed content
3. Fragmented text from OCR-induced errors
4. Line-by-line scanning for better pattern matching
"""

import os
import sys
import django

# Setup Django environment
sys.path.append('/code')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'extractor_project.settings')
django.setup()

from extractor.utils.extractor import (
    detect_multilingual_content,
    create_multilingual_patterns,
    extract_with_line_by_line_scan,
    extract_entries_from_text
)

def test_multilingual_detection():
    """Test multilingual content detection."""
    print("=== Testing Multilingual Detection ===")
    
    # Test cases
    test_cases = [
        {
            'text': 'Part No: PP12345678 Heat No: SU123456',
            'expected': (False, False),
            'description': 'Standard English text'
        },
        {
            'text': 'Part No\n\n: PP12345678\n\nHeat   No  :  SU123456',
            'expected': (False, True),
            'description': 'Fragmented English text'
        },
        {
            'text': '零件号 Part No: PP12345678 炉号 Heat No: SU123456',
            'expected': (True, False),
            'description': 'Mixed Chinese-English text'
        },
        {
            'text': '零件号\nPart No\n\n: PP12345678\n炉号   Heat   No  :  SU123456',
            'expected': (True, True),
            'description': 'Mixed Chinese-English fragmented text'
        }
    ]
    
    for i, case in enumerate(test_cases, 1):
        is_multilingual, has_fragmentation = detect_multilingual_content(case['text'])
        result = (is_multilingual, has_fragmentation)
        status = "✅" if result == case['expected'] else "❌"
        
        print(f"Test {i}: {status} {case['description']}")
        print(f"  Text: {repr(case['text'][:50])}...")
        print(f"  Expected: {case['expected']}")
        print(f"  Got: {result}")
        print()

def test_multilingual_patterns():
    """Test multilingual pattern creation."""
    print("=== Testing Multilingual Pattern Creation ===")
    
    base_pattern = r'\bPP\d{8,12}(?:-\d+)?\b'
    patterns = create_multilingual_patterns(base_pattern, 'PLATE_NO')
    
    print(f"Base pattern: {base_pattern}")
    print(f"Generated {len(patterns)} enhanced patterns:")
    for i, pattern in enumerate(patterns, 1):
        print(f"  {i}. {pattern}")
    print()

def test_line_by_line_extraction():
    """Test line-by-line extraction with sample multilingual text."""
    print("=== Testing Line-by-Line Extraction ===")
    
    # Sample vendor config
    vendor_config = {
        "vendor_id": "test_multilingual",
        "vendor_name": "Test Multilingual Vendor",
        "fields": {
            "PLATE_NO": r'\bPP\d{8,12}(?:-\d+)?\b',
            "HEAT_NO": r'\bSU\d{5,8}\b',
            "TEST_CERT_NO": r'\b\d{6}-FP\d{2}[A-Z]{2}-\d{4}[A-Z]\d-\d{4}\b'
        }
    }
    
    # Test cases with different levels of complexity
    test_cases = [
        {
            'text': '''
            Certificate Number: 123456-FP01AB-2024C1-0001
            Part No: PP123456789
            Heat No: SU12345
            ''',
            'description': 'Standard format'
        },
        {
            'text': '''
            零件号 Part
            No    :    PP123456789
            
            炉号 Heat
            No:
            SU12345
            
            Certificate Number:
            123456-FP01AB-2024C1-0001
            ''',
            'description': 'Fragmented multilingual format'
        },
        {
            'text': '''
            产品号：PP123456789
            批号：SU12345
            证书号：123456-FP01AB-2024C1-0001
            ''',
            'description': 'Chinese labels with English values'
        }
    ]
    
    for i, case in enumerate(test_cases, 1):
        print(f"Test Case {i}: {case['description']}")
        print(f"Input text:")
        print(case['text'])
        
        entries = extract_with_line_by_line_scan(case['text'], vendor_config)
        
        print(f"Extracted {len(entries)} entries:")
        for j, entry in enumerate(entries, 1):
            print(f"  Entry {j}:")
            print(f"    PLATE_NO: {entry.get('PLATE_NO', 'NA')}")
            print(f"    HEAT_NO: {entry.get('HEAT_NO', 'NA')}")
            print(f"    TEST_CERT_NO: {entry.get('TEST_CERT_NO', 'NA')}")
        print()

def test_enhanced_extraction_integration():
    """Test the full enhanced extraction system."""
    print("=== Testing Enhanced Extraction Integration ===")
    
    vendor_config = {
        "vendor_id": "posco",
        "vendor_name": "POSCO International Corporation",
        "fields": {
            "PLATE_NO": r'\bPP\d{8,12}(?:-\d+)?\b',
            "HEAT_NO": r'\bSU\d{5,8}\b',
            "TEST_CERT_NO": r'\b\d{6}-FP\d{2}[A-Z]{2}-\d{4}[A-Z]\d-\d{4}\b'
        }
    }
    
    # Test with multilingual fragmented content
    multilingual_text = '''
    测试证书 Test Certificate
    
    零件号
    Part No    :    PP123456789-1
    
    炉号
    Heat No:
    SU123456
    
    Certificate Number:
    234567-FP02CD-2024D2-0123
    
    Additional parts:
    Part No: PP987654321
    Heat No: SU789012
    '''
    
    print("Testing with multilingual fragmented content:")
    print(multilingual_text)
    
    entries = extract_entries_from_text(multilingual_text, vendor_config)
    
    print(f"\nExtracted {len(entries)} entries using enhanced extraction:")
    for i, entry in enumerate(entries, 1):
        print(f"Entry {i}:")
        print(f"  PLATE_NO: {entry.get('PLATE_NO', 'NA')}")
        print(f"  HEAT_NO: {entry.get('HEAT_NO', 'NA')}")
        print(f"  TEST_CERT_NO: {entry.get('TEST_CERT_NO', 'NA')}")
    print()

def main():
    """Run all tests."""
    print("🚀 Testing Enhanced Multilingual PDF Extraction System")
    print("=" * 60)
    
    test_multilingual_detection()
    test_multilingual_patterns()
    test_line_by_line_extraction()
    test_enhanced_extraction_integration()
    
    print("✅ All tests completed!")
    print("\n📋 Summary of Enhancements:")
    print("• Multilingual content detection (Chinese, Japanese, Korean + English)")
    print("• Fragmentation tolerance for OCR-induced text splitting")
    print("• Line-by-line scanning with flexible regex patterns")
    print("• Enhanced pattern matching with multilingual labels")
    print("• Backward compatibility with existing single-language PDFs")
    print("• Support for advanced table detection libraries (when available)")

if __name__ == "__main__":
    main()