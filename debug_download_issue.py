#!/usr/bin/env python3
"""
Debug script to analyze extracted data and check download package issues
"""

import os
import django
import sys

# Add the project directory to Python path and set up Django
sys.path.append('/mnt/c/Users/Mayank/Desktop/DEE/extractor_project')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'extractor_project.settings')
django.setup()

from extractor.models import UploadedPDF, ExtractedData
from django.conf import settings

def analyze_pdf_extraction(pdf_filename=None):
    """Analyze extraction data for a specific PDF"""
    
    print("🔍 Analyzing PDF Extraction Data...")
    print("=" * 60)
    
    # Find the PDF from the screenshot
    if pdf_filename:
        pdfs = UploadedPDF.objects.filter(file__icontains=pdf_filename)
    else:
        pdfs = UploadedPDF.objects.filter(file__icontains="Pages from Binder1")
    
    if not pdfs.exists():
        print("❌ No PDFs found matching the criteria")
        return
    
    pdf = pdfs.first()
    print(f"📄 Found PDF: {pdf.file.name}")
    print(f"   ID: {pdf.id}")
    print(f"   Vendor: {pdf.vendor.name}")
    print(f"   Status: {pdf.status}")
    print(f"   Upload Date: {pdf.uploaded_at}")
    
    # Get extracted data
    extracted_data = ExtractedData.objects.filter(pdf=pdf).order_by('page_number', 'field_key')
    
    print(f"\n📊 Extracted Data Analysis:")
    print(f"   Total Extracted Fields: {extracted_data.count()}")
    
    if not extracted_data.exists():
        print("❌ No extracted data found")
        return
    
    # Group by page and combination
    combinations = {}
    
    for item in extracted_data:
        page_key = f"page_{item.page_number}"
        if page_key not in combinations:
            combinations[page_key] = {
                'page': item.page_number,
                'PLATE_NO': '', 'HEAT_NO': '', 'TEST_CERT_NO': '',
                'created_at': item.created_at,
                'fields_count': 0
            }
        
        combinations[page_key]['fields_count'] += 1
        if item.field_key in ['PLATE_NO', 'HEAT_NO', 'TEST_CERT_NO']:
            combinations[page_key][item.field_key] = item.field_value
    
    print(f"\n📋 Combinations Found ({len(combinations)}):")
    print("-" * 50)
    
    for i, (page_key, combo) in enumerate(combinations.items(), 1):
        print(f"\n{i}. Page {combo['page']}:")
        print(f"   PLATE_NO: '{combo['PLATE_NO']}'")
        print(f"   HEAT_NO: '{combo['HEAT_NO']}'")
        print(f"   TEST_CERT_NO: '{combo['TEST_CERT_NO']}'")
        print(f"   Fields: {combo['fields_count']}")
        print(f"   Created: {combo['created_at']}")
        
        # Generate expected filename for this combination
        plate_no = combo['PLATE_NO'].replace('/', '-') if combo['PLATE_NO'] else ''
        heat_no = combo['HEAT_NO'].replace('/', '-') if combo['HEAT_NO'] else ''
        test_cert = combo['TEST_CERT_NO'].replace('/', '-') if combo['TEST_CERT_NO'] else ''
        
        if plate_no or heat_no or test_cert:
            expected_filename = f"{heat_no}_{plate_no}_{test_cert}.pdf"
        else:
            expected_filename = f"page_{combo['page']}.pdf"
        
        print(f"   Expected Filename: {expected_filename}")
    
    # Check extracted files directory
    media_root = os.path.abspath(settings.MEDIA_ROOT)
    extracted_dir = os.path.join(media_root, "extracted")
    
    print(f"\n📁 Checking Extracted Files Directory:")
    print(f"   Media Root: {media_root}")
    print(f"   Extracted Dir: {extracted_dir}")
    
    if not os.path.exists(extracted_dir):
        print("❌ Extracted directory does not exist")
        return
    
    # Look for vendor folders
    vendor_folders = [d for d in os.listdir(extracted_dir) 
                     if os.path.isdir(os.path.join(extracted_dir, d))]
    
    print(f"\n🏢 Available Vendor Folders ({len(vendor_folders)}):")
    for folder in vendor_folders:
        print(f"   - {folder}")
    
    # Try to map vendor name to folder
    vendor_name = pdf.vendor.name
    vendor_folder_candidates = []
    
    # Direct match
    vendor_clean = vendor_name.replace(' ', '_').lower()
    if vendor_clean in [f.lower() for f in vendor_folders]:
        vendor_folder_candidates.append(vendor_clean)
    
    # Fuzzy match
    vendor_parts = vendor_name.upper().split()
    for folder in vendor_folders:
        folder_upper = folder.upper()
        if any(part in folder_upper for part in vendor_parts if len(part) > 3):
            vendor_folder_candidates.append(folder)
    
    print(f"\n🎯 Vendor Folder Matching:")
    print(f"   PDF Vendor: '{vendor_name}'")
    print(f"   Candidates: {vendor_folder_candidates}")
    
    # Check files in candidate folders
    total_pdf_files = 0
    matching_files = []
    
    for folder_name in set(vendor_folder_candidates):
        folder_path = os.path.join(extracted_dir, folder_name)
        if os.path.exists(folder_path):
            pdf_files = [f for f in os.listdir(folder_path) if f.lower().endswith('.pdf')]
            total_pdf_files += len(pdf_files)
            
            print(f"\n📂 Files in '{folder_name}' ({len(pdf_files)} PDFs):")
            
            for pdf_file in pdf_files:
                print(f"   - {pdf_file}")
                
                # Check if this file matches any of our combinations
                file_lower = pdf_file.lower().replace('-', '_').replace(' ', '_')
                
                for page_key, combo in combinations.items():
                    plate_no = combo['PLATE_NO'].lower().replace('/', '_').replace('-', '_') if combo['PLATE_NO'] else ''
                    heat_no = combo['HEAT_NO'].lower().replace('/', '_').replace('-', '_') if combo['HEAT_NO'] else ''
                    test_cert = combo['TEST_CERT_NO'].lower().replace('/', '_').replace('-', '_') if combo['TEST_CERT_NO'] else ''
                    
                    if ((plate_no and plate_no in file_lower) or
                        (heat_no and heat_no in file_lower) or
                        (test_cert and test_cert in file_lower)):
                        matching_files.append((pdf_file, combo['page'], folder_name))
                        print(f"     ✅ Matches Page {combo['page']} combination")
                        break
    
    print(f"\n📊 Summary:")
    print(f"   Total Combinations: {len(combinations)}")
    print(f"   Total PDF Files in Vendor Folders: {total_pdf_files}")
    print(f"   Matching Files Found: {len(matching_files)}")
    
    if len(matching_files) < len(combinations):
        print(f"⚠️  Issue: Found {len(matching_files)} matching files but expected {len(combinations)}")
        print("   This explains why the download package only contains some files!")
    
    print(f"\n🎯 Files that should be in download package:")
    for i, (filename, page, folder) in enumerate(matching_files, 1):
        print(f"   {i}. {filename} (Page {page}, from {folder}/)")
    
    print(f"\n💡 Recommendations:")
    if len(matching_files) < len(combinations):
        print("   - Review file matching logic in create_single_file_package()")
        print("   - Check if extracted PDF filenames match expected patterns")
        print("   - Verify all combinations are being processed correctly")
    else:
        print("   - File matching seems correct")
        print("   - Issue may be in ZIP creation or deduplication logic")

if __name__ == "__main__":
    analyze_pdf_extraction()