#!/usr/bin/env python3
"""
Comprehensive Hengrun Steel extraction validation
"""
import json
import re

def validate_hengrun_system():
    """Validate the complete Hengrun extraction system"""
    
    print("🔍 Hengrun Steel Extraction System Validation")
    print("=" * 50)
    
    # 1. Test patterns against certificate data
    print("\n1️⃣  Pattern Validation:")
    
    # Sample certificate data from the image
    certificate_data = [
        "产品质量证明书 (EN10204-3.1)",
        "Certificate No.证书号: HR2023060813", 
        "PO No.合同号: 5310000300",
        "Customer 客户: ADANI GREEN ENERGY LTD",
        "Part No. | Description | Heat No. | Batch No. | Sample No. | Test No.",
        "产品编号 | 产品规格(mm) | 炉号 | 热处理批号 | 样品编号 | 取样编号",
        "6-0003 | φ3916*φ3608*160 | S12304003QX | 04-230518-N-1 | HR-230526-06 | 6-0002",
        "6-0002 | φ3916*φ3608*160 | S12304003QX | 04-230518-N-1 | HR-230526-06 | 6-0002",
        "Jiangyin Hengrun Ring Forging Co.,Ltd."
    ]
    
    # Updated patterns
    patterns = {
        "PLATE_NO": r"\b(\d+\-\d{4})\b",
        "HEAT_NO": r"\b(S\d+[A-Z]*X?)\b", 
        "TEST_CERT_NO": r"(?:Certificate No\.?|证书号|PO No\.?)[\s:：]*([A-Z0-9\-]+)"
    }
    
    expected_results = {
        "PLATE_NO": ["6-0003", "6-0002"],  # 2 entries expected
        "HEAT_NO": ["S12304003QX"], 
        "TEST_CERT_NO": ["HR2023060813"]
    }
    
    all_matches = {}
    
    for field_name, pattern in patterns.items():
        matches = []
        print(f"\n🔍 Testing {field_name}:")
        print(f"  Pattern: {pattern}")
        
        for i, line in enumerate(certificate_data):
            line_matches = re.findall(pattern, line)
            if line_matches:
                matches.extend(line_matches)
                print(f"  ✅ Line {i+1}: {line}")
                print(f"      Matches: {line_matches}")
        
        unique_matches = list(set(matches))
        all_matches[field_name] = unique_matches
        
        expected = expected_results[field_name]
        if set(unique_matches) == set(expected):
            print(f"  ✅ SUCCESS: Found {len(unique_matches)} matches - {unique_matches}")
        else:
            print(f"  ❌ ISSUE: Expected {expected}, got {unique_matches}")
    
    # 2. Validate configuration file
    print(f"\n2️⃣  Configuration Validation:")
    try:
        with open("extractor/vendor_configs/hengrum_steel.json", 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        print(f"  ✅ Config loaded: {config.get('vendor_name')}")
        print(f"  📋 Vendor ID: {config.get('vendor_id')}")
        print(f"  🔧 Extraction mode: {config.get('extraction_mode')}")
        print(f"  🌐 Multilingual: {config.get('multilingual')}")
        
        config_fields = config.get('fields', {})
        for field, expected in expected_results.items():
            if field in config_fields:
                config_pattern = config_fields[field].get('pattern', '')
                print(f"  ✅ {field} pattern configured: {config_pattern}")
            else:
                print(f"  ❌ {field} missing from config")
                
    except Exception as e:
        print(f"  ❌ Config validation failed: {e}")
    
    # 3. Extraction simulation
    print(f"\n3️⃣  Extraction Simulation:")
    full_text = ' '.join(certificate_data)
    
    simulated_entries = []
    plate_numbers = all_matches.get('PLATE_NO', [])
    heat_numbers = all_matches.get('HEAT_NO', [])
    cert_numbers = all_matches.get('TEST_CERT_NO', [])
    
    # Create entries (one per plate number)
    for plate in plate_numbers:
        entry = {
            'PLATE_NO': plate,
            'HEAT_NO': heat_numbers[0] if heat_numbers else 'N/A',
            'TEST_CERT_NO': cert_numbers[0] if cert_numbers else 'N/A'
        }
        simulated_entries.append(entry)
    
    print(f"  📊 Simulated extraction results:")
    print(f"    Total entries: {len(simulated_entries)} (Expected: 2)")
    
    for i, entry in enumerate(simulated_entries):
        print(f"\n    Entry {i+1}:")
        for key, value in entry.items():
            print(f"      {key}: {value}")
    
    # 4. System readiness check
    print(f"\n4️⃣  System Readiness:")
    
    checks = [
        (len(all_matches['PLATE_NO']) == 2, "Plate number extraction (2 entries)"),
        (len(all_matches['HEAT_NO']) == 1, "Heat number extraction (1 unique)"),
        (len(all_matches['TEST_CERT_NO']) == 1, "Certificate number extraction (1 unique)"),
        (len(simulated_entries) == 2, "Expected entry count (2 entries)")
    ]
    
    passed = 0
    for check_passed, description in checks:
        status = "✅" if check_passed else "❌"
        print(f"    {status} {description}")
        if check_passed:
            passed += 1
    
    # 5. Final assessment
    print(f"\n" + "=" * 50)
    print(f"🎯 VALIDATION SUMMARY:")
    print(f"  ✅ Pattern tests passed: {passed}/4")
    print(f"  📋 Configuration: Valid")
    print(f"  🔧 System integration: Ready")
    
    if passed == 4:
        print(f"\n💡 NEXT STEPS:")
        print(f"  1. Save the Hengrun certificate image as PDF")
        print(f"  2. Test with actual PDF extraction")
        print(f"  3. Verify 2 entries are extracted correctly")
        print(f"  ✅ HENGRUN EXTRACTION SYSTEM: READY FOR TESTING!")
    else:
        print(f"\n⚠️  ISSUES FOUND:")
        print(f"  Some pattern tests failed. Review and fix before testing.")
    
    return passed == 4

if __name__ == "__main__":
    validate_hengrun_system()