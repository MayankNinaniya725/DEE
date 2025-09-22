#!/usr/bin/env python3
"""
Test Hengrun Steel extraction patterns and identify issues
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

def test_hengrun_patterns():
    """Test Hengrun patterns against the certificate content"""
    
    print("🔍 Hengrun Steel Certificate Analysis")
    print("=" * 50)
    
    # Load Hengrun config
    config_path = "extractor/vendor_configs/hengrun_steel_fixed.json"
    vendor_config = load_vendor_config(config_path)
    
    if not vendor_config:
        print("❌ Failed to load Hengrun config")
        return
        
    print(f"✅ Loaded config: {vendor_config.get('vendor_name')}")
    print(f"📋 Fields: {list(vendor_config.get('fields', {}).keys())}")
    
    # Sample data from the certificate image
    sample_text_lines = [
        "产品质量证明书 (EN10204-3.1)",
        "Certificate No.证书号: HR2023060813",
        "PO No.合同号: 5310000300",
        "Customer 客户: ADANI GREEN ENERGY LTD",
        "Date日期: 2023/6/15",
        "Part No. | Description | Heat No. | Batch No. | Sample No. | Test No.",
        "产品编号 | 产品规格(mm) | 炉号 | 热处理批号 | 样品编号 | 取样编号",
        "6-0003 | φ3916*φ3608*160 | S12304003QX | 04-230518-N-1 | HR-230526-06 | 6-0002",
        "6-0002 | φ3916*φ3608*160 | S12304003QX | 04-230518-N-1 | HR-230526-06 | 6-0002",
        "Heat No. 炉号: S12304003QX",
        "Jiangyin Hengrun Ring Forging Co.,Ltd.",
        "Zhutang Industrial Zone, Jiangyin City,",
        "Jiangsu Province, China 214415"
    ]
    
    print(f"\n🧪 Testing Current Patterns:")
    
    # Get patterns from config
    patterns = vendor_config.get('fields', {})
    
    for field_name, field_config in patterns.items():
        pattern = field_config.get('pattern', '')
        print(f"\n📋 {field_name}:")
        print(f"  Pattern: {pattern}")
        
        matches = []
        for i, line in enumerate(sample_text_lines):
            line_matches = re.findall(pattern, line, re.IGNORECASE)
            if line_matches:
                matches.extend(line_matches)
                print(f"  ✅ Line {i+1}: {line}")
                print(f"      Matches: {line_matches}")
        
        print(f"  📊 Total matches: {len(matches)}")
        if matches:
            print(f"  🎯 Values found: {list(set(matches))}")
        else:
            print(f"  ❌ No matches found - pattern may need adjustment")
    
    # Expected values from the certificate
    expected_values = {
        "PLATE_NO": ["6-0003", "6-0002"],  # 2 entries expected
        "HEAT_NO": ["S12304003QX"],
        "TEST_CERT_NO": ["HR2023060813"]
    }
    
    print(f"\n📊 Expected vs Found Analysis:")
    for field, expected in expected_values.items():
        pattern = patterns.get(field, {}).get('pattern', '')
        found = []
        
        full_text = ' '.join(sample_text_lines)
        matches = re.findall(pattern, full_text, re.IGNORECASE)
        found = list(set(matches))
        
        print(f"\n{field}:")
        print(f"  Expected: {expected}")
        print(f"  Found: {found}")
        
        if set(found) == set(expected):
            print(f"  ✅ MATCH: Pattern working correctly")
        else:
            print(f"  ❌ MISMATCH: Pattern needs adjustment")
            
            # Suggest pattern improvements
            if field == "PLATE_NO" and not found:
                print(f"  💡 Suggestion: Try pattern: (\\d+-\\d{4})")
            elif field == "HEAT_NO" and not found:
                print(f"  💡 Suggestion: Try pattern: (S\\d+[A-Z]*X?)")
            elif field == "TEST_CERT_NO" and not found:
                print(f"  💡 Suggestion: Try pattern: (HR\\d+)")
    
    # Test if we need to save a PDF for actual extraction testing
    print(f"\n📄 PDF Testing:")
    print("To test with actual PDF extraction:")
    print("1. Save the certificate image as PDF")
    print("2. Place it in media/ directory") 
    print("3. Run extraction test similar to POSCO")
    print("Expected result: 2 entries (for part numbers 6-0003 and 6-0002)")

if __name__ == "__main__":
    test_hengrun_patterns()