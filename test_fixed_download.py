#!/usr/bin/env python3
"""
Test the fixed download package functionality
"""

import os
import django
import sys
import tempfile
import zipfile

# Add the project directory to Python path and set up Django
sys.path.append('/mnt/c/Users/Mayank/Desktop/DEE/extractor_project')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'extractor_project.settings')
django.setup()

from extractor.models import UploadedPDF
from extractor.views.single_file_package import create_single_file_package

def test_fixed_download():
    """Test the fixed download functionality"""
    
    print("🧪 Testing Fixed Download Package Functionality...")
    print("=" * 60)
    
    # Find the PDF from our previous analysis
    pdf = UploadedPDF.objects.filter(file__icontains="Pages from Binder1").first()
    
    if not pdf:
        print("❌ Test PDF not found")
        return
    
    print(f"📄 Testing with PDF: {pdf.file.name} (ID: {pdf.id})")
    print(f"   Vendor: {pdf.vendor.name}")
    print(f"   Status: {pdf.status}")
    
    # Test the package creation
    print(f"\n🔨 Creating package...")
    
    try:
        success, result = create_single_file_package(pdf.id)
        
        if not success:
            print(f"❌ Package creation failed: {result}")
            return
        
        # Unpack result
        buffer, zip_filename, stats = result
        
        print(f"✅ Package created successfully!")
        print(f"   Filename: {zip_filename}")
        print(f"   PDF Count: {stats['pdf_count']}")
        print(f"   Excel Included: {stats['excel_included']}")
        print(f"   Errors: {len(stats.get('errors', []))}")
        
        # Analyze the ZIP contents
        buffer.seek(0)
        buffer_size = len(buffer.getvalue())
        print(f"   Buffer Size: {buffer_size} bytes")
        
        # Extract and examine ZIP contents
        buffer.seek(0)
        
        with tempfile.NamedTemporaryFile(delete=False, suffix='.zip') as temp_zip:
            temp_zip.write(buffer.getvalue())
            temp_zip_path = temp_zip.name
        
        print(f"\n📦 ZIP Contents Analysis:")
        print("-" * 40)
        
        try:
            with zipfile.ZipFile(temp_zip_path, 'r') as zip_ref:
                file_list = zip_ref.namelist()
                
                print(f"Total files in ZIP: {len(file_list)}")
                
                # Categorize files
                original_pdfs = [f for f in file_list if f.startswith('original/')]
                extracted_pdfs = [f for f in file_list if f.startswith('extracted_pdfs/')]
                excel_files = [f for f in file_list if f.endswith('.xlsx')]
                other_files = [f for f in file_list if f not in original_pdfs + extracted_pdfs + excel_files]
                
                print(f"\n📂 File Categories:")
                print(f"   Original PDFs: {len(original_pdfs)}")
                for f in original_pdfs:
                    print(f"     - {f}")
                
                print(f"   Extracted PDFs: {len(extracted_pdfs)}")
                for f in extracted_pdfs:
                    print(f"     - {f}")
                    
                print(f"   Excel Files: {len(excel_files)}")
                for f in excel_files:
                    print(f"     - {f}")
                    
                print(f"   Other Files: {len(other_files)}")
                for f in other_files:
                    print(f"     - {f}")
                
                # Check if we have multiple extracted PDFs (this was the issue)
                if len(extracted_pdfs) >= 2:
                    print(f"\n✅ SUCCESS: Found {len(extracted_pdfs)} extracted PDFs!")
                    print("   This should fix the issue where only 1 file was showing in downloads.")
                elif len(extracted_pdfs) == 1:
                    print(f"\n⚠️  Still only 1 extracted PDF found")
                    print("   The fix might not be working as expected")
                else:
                    print(f"\n❌ No extracted PDFs found")
        
        finally:
            # Clean up temp file
            try:
                os.unlink(temp_zip_path)
            except:
                pass
        
        # Show errors if any
        if stats.get('errors'):
            print(f"\n⚠️  Errors encountered:")
            for error in stats['errors']:
                print(f"   - {error}")
        
        print(f"\n🎯 Expected Result:")
        print("   - Original PDF: Pages from Binder1.pdf")
        print("   - Extracted PDFs: T5119005010_S500107_Z202502190000925.pdf")
        print("   -                 T5119005020_S500107_Z202502190000925.pdf")
        print("   - Excel file with extraction data")
        print("   - README.txt file")
        
        return True
        
    except Exception as e:
        print(f"❌ Error during testing: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_fixed_download()
    if success:
        print("\n🎉 Test completed!")
    else:
        print("\n❌ Test failed!")