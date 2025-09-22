#!/usr/bin/env python3
"""
Comprehensive validation of Iraeta Energy Equipment extraction system
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

from extractor.utils.config_loader import load_vendor_config
import re
import json

def validate_iraeta_system():
    """Validate the complete Iraeta extraction system"""
    
    print("🔍 Iraeta Energy Equipment Extraction System Validation")
    print("=" * 60)
    
    # 1. Test patterns against certificate data
    print("\n1️⃣  Pattern Validation:")
    
    # Sample certificate data from the image
    certificate_data = [
        "伊莱特能源装备股份有限公司",
        "Iraeta Energy Equipment Co., Ltd.",
        "产品质量证明书",
        "Product Quality Certificate",
        "日期/Date: 2025 年/Year 1 月/Month 11 日/Day",
        "订货单位 Purchaser: Welspun New Energy Limited",
        "材料名称 Grade: S355NL",
        "技术条件 Technical Specification: TS-0005698_Technical Specification for Tower",
        "工件号 Part No.: 24-3765-11  24-3765-12",
        "24-3765-13  24-3765-14",
        "24-3765-15  24-3765-16", 
        "24-3765-17  24-3765-18",
        "数量 Quantity: 8",
        "炉号 Heat No.: SI24-4260",
        "尺寸 Size: 4495/3850*175/135",
        "锻造比 Forging ratio: 9.18",
        "交货状态 Delivery condition: 正火 N",
        "热处理炉号 Heat treatment No.: 245-2-255",
        "试样编号 Sample No.: 24-3765-14 (245-3507)",
        "报告编号 Report No.: 2024-3765-002"
    ]
    
    # Load updated config
    config_path = "extractor/vendor_configs/iraeta_steel.json"
    try:
        vendor_config = load_vendor_config(config_path)
        print(f"✅ Loaded config: {vendor_config.get('vendor_name')}")
        
        patterns = vendor_config.get('fields', {})
        
    except Exception as e:
        print(f"❌ Failed to load config: {e}")
        return False
    
    # Expected values
    expected_results = {
        "PLATE_NO": ["24-3765-11", "24-3765-12", "24-3765-13", "24-3765-14", 
                     "24-3765-15", "24-3765-16", "24-3765-17", "24-3765-18"],  # 8 entries
        "HEAT_NO": ["SI24-4260"],
        "TEST_CERT_NO": ["2024-3765-002"]
    }
    
    all_matches = {}
    
    for field_name, field_config in patterns.items():
        pattern = field_config.get('pattern', '')
        print(f"\n🔍 Testing {field_name}:")
        print(f"  Pattern: {pattern}")
        
        matches = []
        full_text = ' '.join(certificate_data)
        
        # Extract matches
        line_matches = re.findall(pattern, full_text, re.IGNORECASE)
        matches.extend(line_matches)
        
        unique_matches = list(set(matches))
        all_matches[field_name] = unique_matches
        
        expected = expected_results[field_name]
        print(f"  📊 Found: {len(unique_matches)} matches")
        print(f"  🎯 Expected: {len(expected)} matches")
        
        if set(unique_matches) == set(expected):
            print(f"  ✅ SUCCESS: Pattern working correctly")
            print(f"      Values: {unique_matches}")
        else:
            print(f"  ❌ ISSUE: Pattern needs adjustment")
            print(f"      Found: {unique_matches}")
            print(f"      Expected: {expected}")
    
    # 2. Validate configuration structure
    print(f"\n2️⃣  Configuration Validation:")
    
    required_fields = ['vendor_id', 'vendor_name', 'extraction_mode', 'fields']
    config_valid = True
    
    for field in required_fields:
        if field in vendor_config:
            print(f"  ✅ {field}: {vendor_config[field]}")
        else:
            print(f"  ❌ Missing {field}")
            config_valid = False
    
    # 3. Extraction simulation
    print(f"\n3️⃣  Extraction Simulation:")
    
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
    print(f"    Total entries: {len(simulated_entries)} (Expected: 8)")
    
    for i, entry in enumerate(simulated_entries[:3]):  # Show first 3
        print(f"\n    Entry {i+1}:")
        for key, value in entry.items():
            print(f"      {key}: {value}")
    
    if len(simulated_entries) > 3:
        print(f"\n    ... and {len(simulated_entries) - 3} more entries")
    
    # 4. System readiness check
    print(f"\n4️⃣  System Readiness:")
    
    checks = [
        (len(all_matches.get('PLATE_NO', [])) == 8, "Plate number extraction (8 entries)"),
        (len(all_matches.get('HEAT_NO', [])) == 1, "Heat number extraction (1 unique)"),
        (len(all_matches.get('TEST_CERT_NO', [])) == 1, "Certificate number extraction (1 unique)"),
        (len(simulated_entries) == 8, "Expected entry count (8 entries)"),
        (config_valid, "Configuration structure valid")
    ]
    
    passed = 0
    for check_passed, description in checks:
        status = "✅" if check_passed else "❌"
        print(f"    {status} {description}")
        if check_passed:
            passed += 1
    
    # 5. Final assessment
    print(f"\n" + "=" * 60)
    print(f"🎯 VALIDATION SUMMARY:")
    print(f"  ✅ System tests passed: {passed}/5")
    print(f"  📋 Configuration: {'Valid' if config_valid else 'Invalid'}")
    print(f"  🔧 Pattern matching: {'Working' if passed >= 4 else 'Needs work'}")
    
    success = passed == 5
    
    if success:
        print(f"\n💡 NEXT STEPS:")
        print(f"  1. Save the Iraeta certificate image as PDF")
        print(f"  2. Test with actual PDF extraction")
        print(f"  3. Verify 8 entries are extracted correctly")
        print(f"  ✅ IRAETA EXTRACTION SYSTEM: READY FOR TESTING!")
    else:
        print(f"\n⚠️  ISSUES FOUND:")
        print(f"  Some validation tests failed. Review and fix before testing.")
    
    # Show extraction summary
    print(f"\n📋 Expected Extraction Results:")
    print(f"  • Part Numbers: 24-3765-11 through 24-3765-18 (8 entries)")
    print(f"  • Heat Number: SI24-4260 (shared across all entries)")
    print(f"  • Certificate: 2024-3765-002 (shared across all entries)")
    
    return success

if __name__ == "__main__":
    validate_iraeta_system()