#!/usr/bin/env python3
"""
Check and process DFIPL file regardless of status
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

def check_and_process_dfipl():
    """Check DFIPL file status and process if needed"""
    
    print("🔍 CHECKING DFIPL FILE STATUS")
    print("=" * 50)
    
    # Find the DFIPL file regardless of status
    dfipl_pdf = UploadedPDF.objects.filter(
        file__icontains="DFIPL-WNEL-001-S1-3-9"
    ).first()
    
    if not dfipl_pdf:
        print("❌ No DFIPL file found")
        return False
    
    print(f"📄 Found DFIPL file: {dfipl_pdf.file.name}")
    print(f"   Vendor: {dfipl_pdf.vendor.name}")
    print(f"   Status: {dfipl_pdf.status}")
    
    # Check if already has extracted data
    existing_data = ExtractedData.objects.filter(pdf=dfipl_pdf).count()
    print(f"   Existing data: {existing_data} entries")
    
    if existing_data > 0:
        print("✅ File already has extracted data")
        return True
    
    if dfipl_pdf.status == "ERROR":
        print("🔄 Resetting ERROR status to PENDING for reprocessing")
        dfipl_pdf.status = "PENDING"
        dfipl_pdf.save()
    
    if dfipl_pdf.status not in ["PENDING", "PROCESSING"]:
        print(f"⚠️  Status is {dfipl_pdf.status}, forcing reprocessing")
        dfipl_pdf.status = "PENDING"
        dfipl_pdf.save()
    
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
        
        print(f"✅ Loaded vendor config from: {config_path}")
        print(f"   Config keys: {list(vendor_config.keys())}")
        
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
        extraction_results, extraction_stats = extract_pdf_fields(pdf_path, vendor_config)
        
        print(f"📊 Extraction results:")
        print(f"   Total entries found: {len(extraction_results)}")
        print(f"   Total pages processed: {extraction_stats['total_pages']}")
        print(f"   Successful pages: {extraction_stats['successful_pages']}")
        
        # Save extracted data
        total_saved = 0
        for entry in extraction_results:
            page_num = entry.get('Page', 1)
            print(f"\n   Entry from Page {page_num}:")
            
            # Extract the key fields and save them to database
            for field_key in ['PLATE_NO', 'HEAT_NO', 'TEST_CERT_NO']:
                if field_key in entry:
                    field_value = entry[field_key]
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

def show_extracted_data():
    """Show the extracted data after processing"""
    
    print(f"\n📋 EXTRACTED DATA SUMMARY")
    print("-" * 30)
    
    # Find the DFIPL file
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
        
        print(f"\n📑 Data by page:")
        for page_num, fields in pages.items():
            print(f"\n  📄 Page {page_num}:")
            for field_key, field_value in fields.items():
                print(f"    {field_key}: {field_value}")
            
            # Generate expected combination name like the Excel does
            plate_no = fields.get('PLATE_NO', '').replace('/', '-')
            heat_no = fields.get('HEAT_NO', '').replace('/', '-')
            test_cert = fields.get('TEST_CERT_NO', '').replace('/', '-')
            
            if plate_no or heat_no or test_cert:
                combo_name = f"{plate_no}_{heat_no}_{test_cert}"
                print(f"    💡 Expected filename: {combo_name}.pdf")
                
                # This is what should appear in Excel
                print(f"    📊 Excel entry should show:")
                print(f"       PLATE_NO: {fields.get('PLATE_NO', '')}")
                print(f"       HEAT_NO: {fields.get('HEAT_NO', '')}")
                print(f"       TEST_CERT_NO: {fields.get('TEST_CERT_NO', '')}")
                print(f"       Filename: {combo_name}.pdf")

if __name__ == "__main__":
    success = check_and_process_dfipl()
    if success:
        show_extracted_data()
        print(f"\n🎉 Processing completed successfully!")
    else:
        print(f"\n❌ Processing failed!")