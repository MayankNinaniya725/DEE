#!/usr/bin/env python3
"""
Get full OCR text and analyze all patterns
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

import re

def analyze_full_ocr_text():
    """Get the complete OCR text and analyze patterns"""
    
    pdf_path = "media/posco_test.pdf"
    
    if not os.path.exists(pdf_path):
        print(f"❌ PDF not found: {pdf_path}")
        return
    
    print(f"🔍 Full OCR Analysis: {pdf_path}")
    print("=" * 60)
    
    try:
        from extractor.utils.ocr_helper import extract_text_with_ocr
        ocr_text = extract_text_with_ocr(pdf_path, 0)  # Page 0
        
        if not ocr_text:
            print("❌ No OCR text extracted")
            return
        
        print(f"📄 Full OCR Text ({len(ocr_text)} characters):")
        print("-" * 40)
        print(ocr_text)
        print("-" * 40)
        
        lines = ocr_text.split('\n')
        print(f"\n📋 Line-by-line analysis ({len(lines)} lines):")
        
        plate_pattern = r"\b(PP\d{8})\b|\b(PP\d{8}-\d{4})\b|\b(PP\d{3}[A-Z]\d{4}(?:-[A-Z]\d{4})?)\b|\b(PP\d{6}[A-Z]=\d{3})\b|\b(PP\d{6}H=\d{3})\b"
        heat_pattern = r"\b(SU\d{5})\b|\b(SU3[0-9][6-9][0-9]{2})\b"
        cert_pattern = r"Certificate\s+No\.\s*[:]*\s*(\d{6}-FP\d{2}[A-Z]{2}-\d{4}[A-Z]\d-\d{4})"
        
        all_plate_matches = []
        all_heat_matches = []
        all_cert_matches = []
        
        for i, line in enumerate(lines):
            line = line.strip()
            if not line:
                continue
                
            print(f"\nLine {i+1:2d}: {line}")
            
            # Check for plate numbers
            plate_matches = re.findall(plate_pattern, line)
            if plate_matches:
                for match_groups in plate_matches:
                    plate_no = next(group for group in match_groups if group)
                    if plate_no:
                        all_plate_matches.append(plate_no)
                        print(f"        📋 PLATE: {plate_no}")
            
            # Check for heat numbers
            heat_matches = re.findall(heat_pattern, line)
            if heat_matches:
                for match_groups in heat_matches:
                    heat_no = next(group for group in match_groups if group)
                    if heat_no:
                        all_heat_matches.append(heat_no)
                        print(f"        🔥 HEAT: {heat_no}")
            
            # Check for certificates
            cert_matches = re.findall(cert_pattern, line)
            if cert_matches:
                for match in cert_matches:
                    all_cert_matches.append(match)
                    print(f"        📜 CERT: {match}")
        
        print(f"\n" + "=" * 60)
        print(f"📊 FINAL SUMMARY:")
        print(f"  Total Plate Numbers: {len(all_plate_matches)}")
        print(f"  Total Heat Numbers: {len(all_heat_matches)}")
        print(f"  Total Certificates: {len(all_cert_matches)}")
        
        if all_plate_matches:
            print(f"\n📋 All Plate Numbers:")
            for i, plate in enumerate(all_plate_matches):
                print(f"  {i+1}: {plate}")
        
        if all_heat_matches:
            print(f"\n🔥 All Heat Numbers:")
            for i, heat in enumerate(set(all_heat_matches)):
                print(f"  {i+1}: {heat}")
        
        if all_cert_matches:
            print(f"\n📜 All Certificates:")
            for i, cert in enumerate(all_cert_matches):
                print(f"  {i+1}: {cert}")
                
    except Exception as e:
        print(f"❌ Analysis failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    analyze_full_ocr_text()