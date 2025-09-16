#!/usr/bin/env python
"""
Debug script to test the download functionality directly
"""
import os
import sys
import django

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'extractor_project.settings')
sys.path.append('/app')
django.setup()

from extractor.views.single_file_package import create_single_file_package
from extractor.models import UploadedPDF

def test_download():
    """Test the download package creation"""
    print("Testing download package creation...")
    
    # Get the first PDF to test with
    try:
        pdf = UploadedPDF.objects.first()
        if not pdf:
            print("No PDFs found in database")
            return
            
        print(f"Testing with PDF: {pdf.id} - {pdf.file.name}")
        
        # Test package creation
        success, result = create_single_file_package(pdf.id)
        
        if success:
            buffer, zip_filename, stats = result
            buffer_size = len(buffer.getvalue())
            print(f"SUCCESS: Package created")
            print(f"  Filename: {zip_filename}")
            print(f"  Buffer size: {buffer_size} bytes")
            print(f"  PDF count: {stats['pdf_count']}")
            print(f"  Excel included: {stats['excel_included']}")
            if stats['errors']:
                print(f"  Errors: {stats['errors']}")
        else:
            print(f"FAILED: {result}")
            
    except Exception as e:
        print(f"ERROR: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_download()