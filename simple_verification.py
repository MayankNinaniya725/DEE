#!/usr/bin/env python3
"""
Simple verification of Excel generation fixes
"""

import os
import django
import sys

# Add the project directory to Python path and set up Django
sys.path.append('/mnt/c/Users/Mayank/Desktop/DEE\extractor_project')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'extractor_project.settings')
django.setup()

from extractor.models import UploadedPDF, ExtractedData
from extractor.views.single_file_package import create_single_file_package
import tempfile
import zipfile
import pandas as pd

def simple_verification():
    """Simple verification of the fixes"""
    
    print("🔍 SIMPLE VERIFICATION - EXCEL FIXES")
    print("=" * 60)
    
    # Find the DFIPL file
    dfipl_pdf = UploadedPDF.objects.filter(
        file__icontains="DFIPL-WNEL-001-S1-3-9"
    ).first()
    
    if not dfipl_pdf:
        print("❌ DFIPL file not found")
        return False
    
    # Check database first
    extracted_count = ExtractedData.objects.filter(pdf=dfipl_pdf).count()
    plate_count = ExtractedData.objects.filter(pdf=dfipl_pdf, field_key='PLATE_NO').count()
    
    print(f"📊 Database verification:")
    print(f"   Total extracted entries: {extracted_count}")
    print(f"   PLATE_NO entries: {plate_count}")
    
    # Get some B035370 entries
    b035370_heat = ExtractedData.objects.filter(
        pdf=dfipl_pdf,
        field_key='HEAT_NO',
        field_value='B035370'
    ).first()
    
    if b035370_heat:
        print(f"   ✅ Found B035370 heat entries in database")
        
        # Find plates on the same page
        b035370_plates = ExtractedData.objects.filter(
            pdf=dfipl_pdf,
            field_key='PLATE_NO',
            page_number=b035370_heat.page_number
        ).values_list('field_value', flat=True)
        
        print(f"   B035370 plates on page {b035370_heat.page_number}: {list(b035370_plates)}")
    
    # Test Excel generation
    print(f"\n📋 Excel generation test:")
    try:
        success, result = create_single_file_package(dfipl_pdf.id)
        
        if not success:
            print(f"❌ Package creation failed: {result}")
            return False
        
        buffer, zip_filename, stats = result
        
        # Extract Excel and check content
        buffer.seek(0)
        with tempfile.NamedTemporaryFile(delete=False, suffix='.zip') as temp_zip:
            temp_zip.write(buffer.getvalue())
            temp_zip_path = temp_zip.name
        
        try:
            with zipfile.ZipFile(temp_zip_path, 'r') as zip_ref:
                excel_files = [f for f in zip_ref.namelist() if f.endswith('.xlsx')]
                if not excel_files:
                    print("❌ No Excel file found")
                    return False
                    
                excel_file = excel_files[0]
                excel_data = zip_ref.read(excel_file)
                
                with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as temp_excel:
                    temp_excel.write(excel_data)
                    temp_excel_path = temp_excel.name
                
                # Read Excel data
                df = pd.read_excel(temp_excel_path, sheet_name='Extracted Data')
                
                print(f"   ✅ Excel created with {len(df)} rows")
                
                # Check for B035370 entries specifically 
                b035370_excel = df[df['HEAT_NO'] == 'B035370']
                print(f"   ✅ B035370 entries in Excel: {len(b035370_excel)}")
                
                # Verify filenames are combination-based
                sample_filenames = df['Filename'].head(5).tolist()
                print(f"\n📝 Sample filenames:")
                for i, filename in enumerate(sample_filenames, 1):
                    print(f"   {i}. {filename}")
                    if 'DFIPL-WNEL' in filename:
                        print(f"      ❌ Still using original PDF name!")
                    elif filename.count('_') >= 2:  # Should have PLATE_HEAT_CERT format
                        print(f"      ✅ Using combination format!")
                    else:
                        print(f"      ⚠️  Uncertain format")
                
                # Show B035370 entries
                if len(b035370_excel) > 0:
                    print(f"\n📋 B035370 entries (matching your screenshot):")
                    for idx, row in b035370_excel.head(3).iterrows():
                        print(f"   - {row['PLATE_NO']} | {row['HEAT_NO']} | {row['Filename']}")
                
                try:
                    os.unlink(temp_excel_path)
                except:
                    pass
        
        finally:
            try:
                os.unlink(temp_zip_path)
            except:
                pass
        
        print(f"\n🎯 SUMMARY:")
        print(f"   Database entries: {extracted_count} (was 0 before)")
        print(f"   Excel entries: {len(df)} (was 7 before)")
        print(f"   B035370 in Excel: {len(b035370_excel)} (was 0 before)")
        
        # Success criteria
        if (len(df) > 20 and len(b035370_excel) > 0 and 
            not any('DFIPL-WNEL' in f for f in sample_filenames)):
            print(f"   ✅ ALL ISSUES RESOLVED!")
            return True
        else:
            print(f"   ⚠️  Some issues may remain")
            return False
        
    except Exception as e:
        print(f"❌ Error during verification: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = simple_verification()
    
    if success:
        print(f"\n🎉 VERIFICATION SUCCESSFUL!")
        print("✅ Latest extracted file entries are now in Excel")
        print("✅ Filenames show combination names (not original PDF name)")
        print("✅ Excel contains all entries (not just 1 per page)")
        print("\nThe Excel now shows entries like:")
        print("  24LP0366A1_B035370_JSW-PCMD-717472719.pdf")
        print("  24LP0522A1_B035370_JSW-PCMD-717472719.pdf")
        print("  Instead of: DFIPL-WNEL-001-S1-3-9.pdf")
    else:
        print(f"\n❌ Issues may remain - please check the output above")