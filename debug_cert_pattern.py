#!/usr/bin/env python3
"""
Fix the TEST_CERT_NO pattern for Iraeta
"""
import re

def test_cert_patterns():
    """Test different certificate patterns"""
    
    test_line = "报告编号 Report No.: 2024-3765-002"
    
    patterns_to_test = [
        r"(?:Report No\\.?)[\\s:：]*(2024-3765-002)",
        r"(?:Report No\\.?|报告编号)[\\s:：]*(2024-3765-002)",
        r"(2024-3765-002)",
        r"\\b(2024-\\d+-\\d+)\\b",
        r"(?:Report No\\.|报告编号)[\\s:：]*([\\d-]+)"
    ]
    
    print("🔍 Testing Certificate Patterns:")
    print(f"Test line: {test_line}")
    print()
    
    for i, pattern in enumerate(patterns_to_test):
        matches = re.findall(pattern, test_line)
        print(f"Pattern {i+1}: {pattern}")
        print(f"Matches: {matches}")
        print()

if __name__ == "__main__":
    test_cert_patterns()