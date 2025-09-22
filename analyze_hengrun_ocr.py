#!/usr/bin/env python3
"""
Analyze the actual OCR content to find the right patterns
"""
import re

def analyze_ocr_content():
    """Analyze the OCR content to find patterns"""
    
    ocr_text = """' INSPECTION CERTIFICATE C€
<2) PF" mn WEAR (EN10204-3.1) CPR Gartre, O035-CPR-A211
Jiangyin Hengrun Ring Forging Co. Ltd. Certificate No.ir-i3: HR20230608013
Zhutang Industrial Zone, Jiangyin City, PONO.4AS: 5310000300
Tera enatoeeaene tt Customer #5": ADANI GREEN ENERGY LTD
Date HHH: 2023/6/15"""
    
    print("🔍 Analyzing OCR Content for Patterns")
    print("=" * 50)
    
    print(f"OCR Sample:")
    print(ocr_text)
    print()
    
    # Look for certificate numbers
    cert_patterns = [
        r"Certificate No\.[^:]*:\s*([A-Z0-9\-]+)",
        r"(HR\d{11})",
        r"(ir-i\d+)"
    ]
    
    print("Testing certificate patterns:")
    for i, pattern in enumerate(cert_patterns):
        matches = re.findall(pattern, ocr_text)
        print(f"  Pattern {i+1}: {pattern}")
        print(f"  Matches: {matches}")
    print()
    
    # The issue is that the PDF appears to be corrupted or the table content
    # is not being extracted properly. Let me check if there's different content.
    
    print("💡 Analysis:")
    print("1. The OCR is not extracting the table content with part numbers")
    print("2. Only certificate info from header is being read")
    print("3. Expected part numbers 6-0003, 6-0002 are not in OCR text")
    print("4. Need to check if this is the same document as the image shown")

if __name__ == "__main__":
    analyze_ocr_content()