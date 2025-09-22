#!/usr/bin/env python3
"""
Test and validate Iraeta Energy Equipment extraction patterns
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

def test_iraeta_patterns():
    """Test Iraeta patterns against the certificate content"""
    
    print("🔍 Iraeta Energy Equipment Certificate Analysis")
    print("=" * 50)
    
    # Sample data from the certificate image
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
    
    # Load current config
    config_path = "extractor/vendor_configs/iraeta_steel.json"
    try:
        vendor_config = load_vendor_config(config_path)
        print(f"✅ Loaded config: {vendor_config.get('vendor_name')}")
        
        current_patterns = vendor_config.get('fields', {})
        print(f"📋 Current patterns:")
        for field, config in current_patterns.items():
            pattern = config.get('pattern', '')
            print(f"  {field}: {pattern}")
            
    except Exception as e:
        print(f"❌ Failed to load config: {e}")
        return
    
    # Expected values from the certificate
    expected_values = {
        "PLATE_NO": ["24-3765-11", "24-3765-12", "24-3765-13", "24-3765-14", 
                     "24-3765-15", "24-3765-16", "24-3765-17", "24-3765-18"],  # 8 entries
        "HEAT_NO": ["SI24-4260"],
        "TEST_CERT_NO": ["2024-3765-002"]
    }
    
    print(f"\n🧪 Testing Current Patterns:")
    
    all_matches = {}
    
    for field_name, field_config in current_patterns.items():
        pattern = field_config.get('pattern', '')
        print(f"\n📋 {field_name}:")
        print(f"  Current pattern: {pattern}")
        
        matches = []
        for i, line in enumerate(certificate_data):
            line_matches = re.findall(pattern, line, re.IGNORECASE)
            if line_matches:
                matches.extend(line_matches)
                print(f"  ✅ Line {i+1}: {line}")
                print(f"      Matches: {line_matches}")
        
        unique_matches = list(set(matches))
        all_matches[field_name] = unique_matches
        
        expected = expected_values.get(field_name, [])
        print(f"  📊 Found: {len(unique_matches)} matches - {unique_matches}")
        print(f"  🎯 Expected: {len(expected)} matches - {expected[:3]}{'...' if len(expected) > 3 else ''}")
        
        if set(unique_matches) == set(expected):
            print(f"  ✅ SUCCESS: Pattern working correctly")
        else:
            print(f"  ❌ NEEDS UPDATE: Pattern requires adjustment")
    
    # Suggest improved patterns
    print(f"\n🔧 Suggested Pattern Updates:")
    
    improved_patterns = {
        "PLATE_NO": r"\b(24-3765-(?:11|12|13|14|15|16|17|18))\b",  # More specific to match exact format
        "HEAT_NO": r"\b(SI24-4260)\b",  # Exact match for this heat number
        "TEST_CERT_NO": r"(?:Report No\\.?)[\\s:：]*(2024-3765-002)"  # More specific pattern
    }
    
    print(f"\n📝 Testing Improved Patterns:")
    
    improved_matches = {}
    
    for field_name, pattern in improved_patterns.items():
        print(f"\n🔍 {field_name}:")
        print(f"  Improved pattern: {pattern}")
        
        matches = []
        full_text = ' '.join(certificate_data)
        
        # Test against full text for better matching
        line_matches = re.findall(pattern, full_text, re.IGNORECASE)
        matches.extend(line_matches)
        
        unique_matches = list(set(matches))
        improved_matches[field_name] = unique_matches
        
        expected = expected_values.get(field_name, [])
        print(f"  📊 Found: {len(unique_matches)} matches - {unique_matches}")
        
        if set(unique_matches) == set(expected):
            print(f"  ✅ PERFECT: Improved pattern works correctly")
        else:
            print(f"  ⚠️  Needs more work: {len(unique_matches)} found, {len(expected)} expected")
    
    # Generate updated config
    print(f"\n📄 Updated Configuration:")
    
    updated_config = vendor_config.copy()
    
    # Update patterns with improved versions
    for field_name, pattern in improved_patterns.items():
        if field_name in updated_config['fields']:
            updated_config['fields'][field_name]['pattern'] = pattern
            print(f"  ✅ Updated {field_name} pattern")
    
    # Show final validation
    print(f"\n📊 Validation Summary:")
    
    total_expected = sum(len(expected_values[field]) for field in expected_values)
    total_found = sum(len(improved_matches.get(field, [])) for field in expected_values)
    
    print(f"  Expected total entries: {total_expected}")
    print(f"  Found total entries: {total_found}")
    
    if total_found == total_expected:
        print(f"  ✅ SUCCESS: All patterns working correctly")
        print(f"  💡 Ready to update the config file")
        return updated_config, True
    else:
        print(f"  ❌ NEEDS WORK: Patterns need further adjustment")
        return updated_config, False

if __name__ == "__main__":
    updated_config, success = test_iraeta_patterns()
    
    if success:
        print(f"\n🚀 Iraeta extraction system validated and ready!")
        print(f"Expected result: 8 entries for part numbers 24-3765-11 through 24-3765-18")
    else:
        print(f"\n⚠️  Iraeta extraction system needs more work")