#!/usr/bin/env python3
"""
Process the DFIPL file and debug the extraction
"""

import os
import django
import sys

# Add the project directory to Python path and set up Django
sys.path.append('/mnt/c/Users/Mayank/Desktop/DEE/extractor_project')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'extractor_project.settings')
django.setup()

from extractor.models import UploadedPDF, ExtractedData
from extractor.utils.extractor import extract_pdf_fields
from extractor.utils.config_loader import find_vendor_config
from django.conf import settings

def process_dfipl_file():
    """Process the DFIPL file that's been pending"""
    
    print("🔄 PROCESSING PENDING DFIPL FILE")
    print("=" * 50)
    
    # Find the DFIPL file
    dfipl_pdf = UploadedPDF.objects.filter(
        file__icontains="DFIPL-WNEL-001-S1-3-9",
        status="PENDING"
    ).first()
    
    if not dfipl_pdf:
        print("❌ No PENDING DFIPL file found")
        return False
    
    print(f"📄 Found DFIPL file: {dfipl_pdf.file.name}")
    print(f"   Vendor: {dfipl_pdf.vendor.name}")
    print(f"   Status: {dfipl_pdf.status}")
    
    try:
        # Update status to PROCESSING
        dfipl_pdf.status = "PROCESSING"
        dfipl_pdf.save()
        print(f"✅ Updated status to PROCESSING")
        
        # Get the vendor config
        vendor_config, config_path = find_vendor_config(dfipl_pdf.vendor, settings)
        if not vendor_config:
            print(f"❌ No vendor config found for {dfipl_pdf.vendor.name}")
            dfipl_pdf.status = "ERROR"
            dfipl_pdf.save()
            return False
        
        print(f"✅ Loaded vendor config for {dfipl_pdf.vendor.name}")
        
        # Get the file path
        pdf_path = dfipl_pdf.file.path
        if not os.path.exists(pdf_path):
            print(f"❌ PDF file not found at: {pdf_path}")
            dfipl_pdf.status = "ERROR"
            dfipl_pdf.save()
            return False
        
        print(f"✅ PDF file found at: {pdf_path}")
        
        # Extract data from the PDF
        print(f"🔍 Starting extraction...")
        extracted_fields = extract_pdf_fields(pdf_path, vendor_config)
        
        print(f"📊 Extraction results:")
        print(f"   Total pages processed: {len(extracted_fields)}")
        
        # Save extracted data
        total_saved = 0
        for page_num, fields in extracted_fields.items():
            print(f"\n   Page {page_num}: {len(fields)} fields")
            
            for field_key, field_value in fields.items():
                print(f"     {field_key}: {field_value}")
                
                # Save to database
                ExtractedData.objects.create(
                    vendor=dfipl_pdf.vendor,
                    pdf=dfipl_pdf,
                    field_key=field_key,
                    field_value=field_value,
                    page_number=page_num
                )
                total_saved += 1
        
        print(f"\n✅ Saved {total_saved} extracted fields to database")
        
        # Update status to COMPLETED
        dfipl_pdf.status = "COMPLETED"
        dfipl_pdf.save()
        print(f"✅ Updated status to COMPLETED")
        
        return True
        
    except Exception as e:
        print(f"❌ Error during processing: {e}")
        import traceback
        traceback.print_exc()
        
        # Update status to ERROR
        dfipl_pdf.status = "ERROR"
        dfipl_pdf.save()
        return False

def check_extracted_data():
    """Check the extracted data after processing"""
    
    print(f"\n📋 CHECKING EXTRACTED DATA")
    print("-" * 30)
    
    # Find the DFIPL file again
    dfipl_pdf = UploadedPDF.objects.filter(
        file__icontains="DFIPL-WNEL-001-S1-3-9"
    ).first()
    
    if not dfipl_pdf:
        print("❌ DFIPL file not found")
        return
    
    print(f"📄 PDF Status: {dfipl_pdf.status}")
    
    # Get extracted data
    extracted_data = ExtractedData.objects.filter(pdf=dfipl_pdf).order_by('page_number', 'field_key')
    
    print(f"📊 Extracted entries: {extracted_data.count()}")
    
    if extracted_data.exists():
        # Group by page
        pages = {}
        for entry in extracted_data:
            if entry.page_number not in pages:
                pages[entry.page_number] = {}
            pages[entry.page_number][entry.field_key] = entry.field_value
        
        for page_num, fields in pages.items():
            print(f"\n  Page {page_num}:")
            for field_key, field_value in fields.items():
                print(f"    {field_key}: {field_value}")
            
            # Generate expected combination name
            plate_no = fields.get('PLATE_NO', '')
            heat_no = fields.get('HEAT_NO', '')
            test_cert = fields.get('TEST_CERT_NO', '')
            
            if plate_no or heat_no or test_cert:
                combo_name = f"{plate_no}_{heat_no}_{test_cert}"
                print(f"    Expected filename: {combo_name}.pdf")

if __name__ == "__main__":
    success = process_dfipl_file()
    if success:
        check_extracted_data()
        print(f"\n🎉 Processing completed successfully!")