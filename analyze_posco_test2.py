#!/usr/bin/env python3
"""
Analyze the second POSCO PDF for breakline issues and 5 entries
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

from extractor.utils.extractor import extract_pdf_fields
from extractor.utils.config_loader import load_vendor_config
import re

def analyze_posco_test2():
    """Analyze the second POSCO PDF for breaklines and extraction issues"""
    
    pdf_path = "media/posco_test2.pdf"
    config_path = "extractor/vendor_configs/posco_steel.json"
    
    if not os.path.exists(pdf_path):
        print(f"❌ PDF not found: {pdf_path}")
        return
    
    print(f"🔍 Analyzing POSCO Test 2: {pdf_path}")
    print("Expected: 5 entries")
    print("=" * 60)
    
    # Load config
    vendor_config = load_vendor_config(config_path)
    if not vendor_config:
        print("❌ Failed to load POSCO config")
        return
        
    print(f"✅ Loaded config: {vendor_config.get('vendor_name')}")
    
    # Get OCR text to analyze breaklines
    try:
        from extractor.utils.ocr_helper import extract_text_with_ocr
        ocr_text = extract_text_with_ocr(pdf_path, 0)  # Page 0
        
        if not ocr_text:
            print("❌ No OCR text extracted")
            return
        
        print(f"\n📄 OCR Text Analysis ({len(ocr_text)} characters):")
        print("-" * 40)
        print(ocr_text[:1000])  # Show first 1000 characters
        if len(ocr_text) > 1000:
            print(f"\n... (showing first 1000 of {len(ocr_text)} characters)")
        print("-" * 40)
        
        lines = ocr_text.split('\n')
        print(f"\n📋 Line Analysis ({len(lines)} total lines):")
        
        # Current patterns
        plate_pattern = r"\b(PP\d{8})\b|\b(PP\d{8}-\d{4})\b|\b(PP\d{3}[A-Z]\d{4}(?:-[A-Z]\d{4})?)\b|\b(PP\d{6}[A-Z]=\d{3})\b|\b(PP\d{6}H=\d{3})\b"
        heat_pattern = r"\b(SU\d{5})\b|\b(SU3[0-9][6-9][0-9]{2})\b"
        cert_pattern = r"Certificate\s+No\.\s*[:]*\s*(\d{6}-FP\d{2}[A-Z]{2}-\d{4}[A-Z]\d-\d{4})"
        
        plate_matches = []
        heat_matches = []
        cert_matches = []
        
        # Analyze each line for patterns and breaklines
        for i, line in enumerate(lines):
            line_stripped = line.strip()
            if not line_stripped:
                continue
            
            # Check for plate patterns
            p_matches = re.findall(plate_pattern, line)
            if p_matches:
                for match_groups in p_matches:
                    plate_no = next(group for group in match_groups if group)
                    if plate_no:
                        plate_matches.append(plate_no)
                        print(f"  Line {i+1:2d}: 📋 PLATE: {plate_no}")
                        print(f"           Full line: {line_stripped}")
            
            # Check for heat patterns
            h_matches = re.findall(heat_pattern, line)
            if h_matches:
                for match_groups in h_matches:
                    heat_no = next(group for group in match_groups if group)
                    if heat_no:
                        heat_matches.append(heat_no)
                        if plate_no not in [m for m in plate_matches if m in line]:  # Only log if not already logged
                            print(f"  Line {i+1:2d}: 🔥 HEAT: {heat_no}")
                            print(f"           Full line: {line_stripped}")
            
            # Check for certificates
            c_matches = re.findall(cert_pattern, line)
            if c_matches:
                for match in c_matches:
                    cert_matches.append(match)
                    print(f"  Line {i+1:2d}: 📜 CERT: {match}")
                    print(f"           Full line: {line_stripped}")
        
        print(f"\n📊 Pattern Analysis Summary:")
        print(f"  Plate Numbers Found: {len(plate_matches)} (Expected: 5)")
        print(f"  Heat Numbers Found: {len(heat_matches)}")
        print(f"  Certificates Found: {len(cert_matches)}")
        
        if len(plate_matches) != 5:
            print(f"\n⚠️  ISSUE: Found {len(plate_matches)} plate numbers, expected 5")
            print("Let me look for potential breakline issues...")
            
            # Look for lines that might contain broken plate numbers
            potential_breaklines = []
            for i, line in enumerate(lines):
                # Look for lines with partial PP patterns or numbers that might be split
                if 'PP' in line or any(re.search(r'\d{6,8}', line) for _ in [1]):
                    if not any(re.search(plate_pattern, line) for _ in [1]):
                        potential_breaklines.append((i+1, line.strip()))
            
            if potential_breaklines:
                print(f"\n🔍 Potential breakline issues found:")
                for line_num, line_text in potential_breaklines[:10]:  # Show first 10
                    print(f"  Line {line_num}: {line_text}")
        
        # Test actual extraction
        print(f"\n🚀 Running Extraction Test:")
        results, stats = extract_pdf_fields(pdf_path, vendor_config)
        
        print(f"\n📊 Extraction Results:")
        print(f"  Total entries: {len(results)} (Expected: 5)")
        print(f"  Pages processed: {stats['successful_pages']}/{stats['total_pages']}")
        print(f"  OCR fallback: {len(stats.get('ocr_fallback_pages', []))}")
        
        if results:
            print(f"\n📝 Extracted entries:")
            for i, entry in enumerate(results):
                print(f"\n  Entry {i+1}:")
                for key in ['PLATE_NO', 'HEAT_NO', 'TEST_CERT_NO', '_corrections_applied']:
                    if key in entry:
                        print(f"    {key}: {entry[key]}")
        
        # Status check
        if len(results) == 5:
            print(f"\n✅ SUCCESS: Extracted exactly 5 entries as expected!")
        else:
            print(f"\n❌ ISSUE: Expected 5 entries, got {len(results)}")
            print("This indicates breakline or pattern matching issues that need fixing.")
            
    except Exception as e:
        print(f"❌ Analysis failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    analyze_posco_test2()