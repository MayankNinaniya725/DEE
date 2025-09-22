#!/usr/bin/env python3
"""
Debug Excel generation and filename issues
"""

import os
import django
import sys

# Add the project directory to Python path and set up Django
sys.path.append('/mnt/c/Users/Mayank/Desktop/DEE/extractor_project')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'extractor_project.settings')
django.setup()

from extractor.models import UploadedPDF, ExtractedData
from django.db.models import Q

def debug_excel_issue():
    """Debug the Excel generation issue"""
    
    print("🔍 DEBUGGING EXCEL GENERATION ISSUE")
    print("=" * 60)
    
    # Find DFIPL files
    dfipl_pdfs = UploadedPDF.objects.filter(file__icontains="DFIPL-WNEL-001-S1-3-9")
    
    print(f"\n📄 DFIPL PDF Files Found: {dfipl_pdfs.count()}")
    print("-" * 40)
    
    for pdf in dfipl_pdfs:
        print(f"\nPDF ID: {pdf.id}")
        print(f"File: {pdf.file.name}")
        print(f"Vendor: {pdf.vendor.name if pdf.vendor else 'None'}")
        print(f"Status: {pdf.status}")
        print(f"Uploaded: {pdf.uploaded_at}")
        
        # Check extracted data for this PDF
        extracted_entries = ExtractedData.objects.filter(pdf=pdf)
        print(f"Extracted entries: {extracted_entries.count()}")
        
        for i, entry in enumerate(extracted_entries, 1):
            print(f"\n  Entry {i}:")
            print(f"    Field Key: {entry.field_key}")
            print(f"    Field Value: {entry.field_value}")
            print(f"    Page Number: {entry.page_number}")
            print(f"    Created: {entry.created_at}")
    
    # Check the latest extracted entries from all files
    print(f"\n📊 LATEST EXTRACTED ENTRIES (All Files)")
    print("-" * 50)
    
    latest_entries = ExtractedData.objects.all().order_by('-id')[:10]
    
    for entry in latest_entries:
        print(f"\nEntry ID: {entry.id}")
        print(f"PDF: {entry.pdf.file.name if entry.pdf else 'None'}")
        print(f"Field Key: {entry.field_key}")
        print(f"Field Value: {entry.field_value}")
        print(f"Page: {entry.page_number}")
        print(f"Created: {entry.created_at}")
    
    # Check if there are any JSW Steel entries
    jsw_entries = ExtractedData.objects.filter(
        Q(field_value__icontains="B035") | 
        Q(field_value__icontains="JSW") |
        Q(field_value__icontains="PCMD")
    )
    
    print(f"\n🏭 JSW/PCMD RELATED ENTRIES: {jsw_entries.count()}")
    print("-" * 40)
    
    for entry in jsw_entries:
        pdf_name = entry.pdf.file.name if entry.pdf else 'None'
        print(f"PDF: {pdf_name}")
        print(f"Field: {entry.field_key} = {entry.field_value}")
        print(f"Entry ID: {entry.id}")
        print("---")

def check_excel_generation_logic():
    """Check how Excel files are generated"""
    
    print(f"\n📋 CHECKING EXCEL GENERATION LOGIC")
    print("-" * 40)
    
    # Look for Excel generation functions
    try:
        # Check single_file_package.py for Excel generation
        with open('/mnt/c/Users/Mayank/Desktop/DEE/extractor_project/extractor/views/single_file_package.py', 'r') as f:
            content = f.read()
            
        if 'xlsx' in content or 'excel' in content.lower():
            print("✅ Excel generation found in single_file_package.py")
        else:
            print("❌ No Excel generation found in single_file_package.py")
            
        # Look for filename generation logic
        if 'combination' in content:
            print("✅ Combination logic found")
        else:
            print("❌ No combination logic found")
            
        # Check for dataframe creation
        if 'DataFrame' in content or 'to_excel' in content:
            print("✅ DataFrame/Excel export found")
        else:
            print("❌ No DataFrame/Excel export found")
            
    except Exception as e:
        print(f"❌ Error reading file: {e}")

if __name__ == "__main__":
    debug_excel_issue()
    check_excel_generation_logic()