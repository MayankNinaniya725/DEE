#!/usr/bin/env python3
"""
Test POSCO extraction with OCR corrections
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

def test_posco_corrections():
    """Test POSCO extraction with heat number corrections"""
    
    # Load POSCO config
    config_path = "extractor/vendor_configs/posco_steel.json"
    vendor_config = load_vendor_config(config_path)
    
    if not vendor_config:
        print("❌ Failed to load POSCO config")
        return
        
    print(f"✅ Loaded POSCO config: {vendor_config.get('vendor_name')}")
    print(f"📋 Fields: {list(vendor_config.get('fields', {}).keys())}")
    
    # Test heat number correction function directly
    from extractor.utils.posco_corrections import apply_posco_corrections
    
    # Test cases
    test_entries = [
        {"HEAT_NO": "SU30682", "PLATE_NO": "Test1"},
        {"HEAT_NO": "SU30882", "PLATE_NO": "Test2"},
        {"HEAT_NO": "SU30082", "PLATE_NO": "Test3"},
        {"HEAT_NO": "OTHER123", "PLATE_NO": "Test4"},
    ]
    
    print("\n🔧 Testing OCR corrections:")
    for entry in test_entries:
        original = entry.copy()
        corrected = apply_posco_corrections(entry)
        if original != corrected:
            print(f"  ✅ {original['HEAT_NO']} → {corrected['HEAT_NO']}")
        else:
            print(f"  ➡️  {original['HEAT_NO']} (no change needed)")
    
    # Check for PDF files to test with
    pdf_files = []
    media_dir = "media"
    if os.path.exists(media_dir):
        for file in os.listdir(media_dir):
            if file.lower().endswith('.pdf'):
                pdf_files.append(os.path.join(media_dir, file))
    
    if pdf_files:
        print(f"\n📄 Found {len(pdf_files)} PDF file(s) for testing")
        test_pdf = pdf_files[0]
        print(f"Testing with: {test_pdf}")
        
        try:
            results, stats = extract_pdf_fields(test_pdf, vendor_config)
            print(f"\n📊 Extraction Results:")
            print(f"  📈 Total entries: {len(results)}")
            print(f"  📄 Pages processed: {stats['successful_pages']}/{stats['total_pages']}")
            print(f"  🔄 OCR used: {len(stats.get('ocr_fallback_pages', []))} pages")
            
            if results:
                print(f"\n📝 Sample entries:")
                for i, entry in enumerate(results[:3]):
                    print(f"  Entry {i+1}:")
                    for key in ["PLATE_NO", "HEAT_NO", "TEST_CERT_NO"]:
                        if key in entry:
                            print(f"    {key}: {entry[key]}")
                    print()
                    
                # Check for heat number issues
                heat_numbers = [r.get('HEAT_NO', '') for r in results if r.get('HEAT_NO')]
                problematic = [h for h in heat_numbers if 'SU306' in h]
                if problematic:
                    print(f"⚠️  Found potentially problematic heat numbers: {problematic}")
                else:
                    print("✅ No problematic heat number patterns found")
                    
        except Exception as e:
            print(f"❌ Extraction failed: {e}")
            import traceback
            traceback.print_exc()
    else:
        print("\n📄 No PDF files found in media directory")
        print("Upload a POSCO certificate to test the complete system")

if __name__ == "__main__":
    test_posco_corrections()