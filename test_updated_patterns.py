#!/usr/bin/env python3
"""
Test updated POSCO patterns with actual OCR text
"""
import re

def test_updated_patterns():
    """Test the updated patterns against OCR text"""
    
    # Sample OCR text from the previous analysis
    sample_lines = [
        "34.8x2692x14151 : PP60654301 : 1 : 10,406 : SU30882 : KOR | T |] 405 580 25 : 414 577) 23: 1: 176 ; : Good L}|C 0.1603 0.374 1.433 0.0127 0.0039 0.040 0.024 2",
        "34,8x2692x14151 : PP60654302 : 1 : 10,406 : SU30882 : KOR | T] 405 580 25 : 414 577) 23: 1: 176 ; : Good L}|C 0.1603 0.374 1.433 0.0127 0.0039 0.040 0,024 2",
        "34.8x2692x14151 : PP60654101-4102 : 2 : 20,812 : SU30882 : KOR | T] 416 570 30 : 414 577) 23: 1: 164 5 : Good L}|C 0.1603 0.374 1.433 0.0127 0.0039 0.040 0,024 2",
        "34.8x2692x14151 : PP60653101 : 1 : 10,406 : SU30882 : KOR | T] 416 570 30 : 414 577) 23: 1: 164 5 : Good L}|C 0.1603 0.374 1.433 0.0127 0.0039 0.040 0,024 2",
        "34.8x2692x14151 : PP60653102 : 1 : 10,406 : SU30882 : KOR | T] 416 570 30 : 414 577) 23: 1: 164 5 : Good L}|C 0.1603 0.374 1.433 0.0127 0.0039 0.040 0,024 2",
        "34.8x2692x14151 : PP60653301 : 1 : 10,406 : SU30882 : KOR | T |] 407 565 30 : 414 577 23: 1: 181 : : Good L | C 0.1603 0.374 1.433 0.0127 0.0039 0.040 0,024 2",
        "34.8x2692x14151 : PP60653302 : 1 : 10,406 : SU30882 : KOR | T] 407 565 30: 414 577 23: 1: 181 : : Good L | C 0.1603 0.374 1.433 0.0127 0.0039 0.040 0.024 2",
        "Mill Test Certificate IS 2062 : 2011 Certificate No. : 241205-FP01KS-0001A1-0001"
    ]
    
    # Updated patterns
    plate_pattern = r"\b(PP\d{8})\b|\b(PP\d{8}-\d{4})\b|\b(PP\d{3}[A-Z]\d{4}(?:-[A-Z]\d{4})?)\b|\b(PP\d{6}[A-Z]=\d{3})\b|\b(PP\d{6}H=\d{3})\b"
    heat_pattern = r"\b(SU\d{5})\b|\b(SU3[0-9][6-9][0-9]{2})\b"
    cert_pattern = r"Certificate\s+No\.\s*[:]*\s*(\d{6}-FP\d{2}[A-Z]{2}-\d{4}[A-Z]\d-\d{4})"
    
    print("🔍 Testing Updated POSCO Patterns")
    print("=" * 50)
    
    # Test plate numbers
    print("\n📋 Plate Number Matches:")
    plate_matches = []
    for i, line in enumerate(sample_lines):
        matches = re.findall(plate_pattern, line)
        for match_groups in matches:
            # Extract the non-empty group
            plate_no = next(group for group in match_groups if group)
            if plate_no:
                plate_matches.append(plate_no)
                print(f"  ✅ Line {i+1}: {plate_no}")
    
    print(f"\n📊 Total plate numbers found: {len(plate_matches)}")
    
    # Test heat numbers
    print("\n🔥 Heat Number Matches:")
    heat_matches = []
    for i, line in enumerate(sample_lines):
        matches = re.findall(heat_pattern, line)
        for match_groups in matches:
            # Extract the non-empty group
            heat_no = next(group for group in match_groups if group)
            if heat_no:
                heat_matches.append(heat_no)
                print(f"  ✅ Line {i+1}: {heat_no}")
    
    print(f"\n📊 Total heat numbers found: {len(heat_matches)}")
    
    # Test certificate numbers
    print("\n📜 Certificate Number Matches:")
    cert_matches = []
    for i, line in enumerate(sample_lines):
        matches = re.findall(cert_pattern, line)
        for match in matches:
            cert_matches.append(match)
            print(f"  ✅ Line {i+1}: {match}")
    
    print(f"\n📊 Total certificate numbers found: {len(cert_matches)}")
    
    # Summary
    print("\n" + "=" * 50)
    print("📈 PATTERN TESTING SUMMARY:")
    print(f"  Plate Numbers: {len(plate_matches)} (Expected: 7)")
    print(f"  Heat Numbers: {len(heat_matches)} (Expected: 7)")
    print(f"  Certificates: {len(cert_matches)} (Expected: 1)")
    
    if len(plate_matches) == 7 and len(cert_matches) == 1:
        print("\n✅ SUCCESS: Patterns should now extract all 7 entries!")
    else:
        print("\n❌ ISSUE: Patterns still need adjustment")
        
    return plate_matches, heat_matches, cert_matches

if __name__ == "__main__":
    test_updated_patterns()