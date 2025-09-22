#!/usr/bin/env python3
"""
Test Excel generation for DFIPL file to verify proper filenames
"""

import os
import django
import sys

# Add the project directory to Python path and set up Django
sys.path.append('/mnt/c/Users/Mayank/Desktop/DEE/extractor_project')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'extractor_project.settings')
django.setup()

from extractor.models import UploadedPDF
from extractor.views.single_file_package import create_single_file_package
import tempfile
import zipfile

def test_dfipl_excel_generation():
    """Test Excel generation for DFIPL file"""
    
    print("📊 TESTING EXCEL GENERATION FOR DFIPL FILE")
    print("=" * 60)
    
    # Find the DFIPL file
    dfipl_pdf = UploadedPDF.objects.filter(
        file__icontains="DFIPL-WNEL-001-S1-3-9"
    ).first()
    
    if not dfipl_pdf:
        print("❌ DFIPL file not found")
        return False
    
    print(f"📄 Testing with DFIPL file: {dfipl_pdf.file.name}")
    print(f"   Vendor: {dfipl_pdf.vendor.name}")
    print(f"   Status: {dfipl_pdf.status}")
    
    # Test the package creation
    print(f"\n🔨 Creating Excel package...")
    
    try:
        success, result = create_single_file_package(dfipl_pdf.id)
        
        if not success:
            print(f"❌ Package creation failed: {result}")
            return False
        
        # Unpack result
        buffer, zip_filename, stats = result
        
        print(f"✅ Package created successfully!")
        print(f"   Filename: {zip_filename}")
        print(f"   Excel Included: {stats['excel_included']}")
        print(f"   PDF Count: {stats['pdf_count']}")
        
        # Extract and examine ZIP contents, focusing on Excel
        buffer.seek(0)
        
        with tempfile.NamedTemporaryFile(delete=False, suffix='.zip') as temp_zip:
            temp_zip.write(buffer.getvalue())
            temp_zip_path = temp_zip.name
        
        try:
            with zipfile.ZipFile(temp_zip_path, 'r') as zip_ref:
                file_list = zip_ref.namelist()
                
                # Find Excel file
                excel_files = [f for f in file_list if f.endswith('.xlsx')]
                
                if not excel_files:
                    print(f"❌ No Excel file found in package")
                    return False
                
                excel_file = excel_files[0]
                print(f"\n📋 Found Excel file: {excel_file}")
                
                # Extract Excel file to examine content
                excel_data = zip_ref.read(excel_file)
                
                with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as temp_excel:
                    temp_excel.write(excel_data)
                    temp_excel_path = temp_excel.name
                
                # Read Excel content
                import pandas as pd
                
                print(f"\n📊 EXCEL CONTENT ANALYSIS:")
                print("-" * 40)
                
                # Read all sheets
                try:
                    excel_sheets = pd.read_excel(temp_excel_path, sheet_name=None)
                    
                    for sheet_name, df in excel_sheets.items():
                        print(f"\n📑 Sheet: {sheet_name}")
                        print(f"   Rows: {len(df)}")
                        print(f"   Columns: {list(df.columns)}")
                        
                        if sheet_name == "Extracted Data" and not df.empty:
                            print(f"\n   📋 Sample entries from Extracted Data:")
                            
                            # Look for entries with B035370 (from your screenshot)
                            if 'HEAT_NO' in df.columns:
                                b035370_entries = df[df['HEAT_NO'].str.contains('B035370', na=False)]
                                
                                if not b035370_entries.empty:
                                    print(f"\n   🎯 Found B035370 entries (from your screenshot):")
                                    for idx, row in b035370_entries.iterrows():
                                        plate_no = row.get('PLATE_NO', 'N/A')
                                        heat_no = row.get('HEAT_NO', 'N/A') 
                                        test_cert = row.get('TEST_CERT_NO', 'N/A')
                                        filename = row.get('Filename', 'N/A')
                                        
                                        print(f"      Row {idx + 1}:")
                                        print(f"        PLATE_NO: {plate_no}")
                                        print(f"        HEAT_NO: {heat_no}")
                                        print(f"        TEST_CERT_NO: {test_cert}")
                                        print(f"        Filename: {filename}")
                                        print(f"        ✅ Expected: {plate_no}_{heat_no}_{test_cert.replace('/', '-')}.pdf")
                                        
                                        # Check if filename matches expected format
                                        expected = f"{plate_no}_{heat_no}_{test_cert.replace('/', '-')}.pdf"
                                        if filename == expected:
                                            print(f"        ✅ CORRECT: Filename matches expected format!")
                                        else:
                                            print(f"        ❌ MISMATCH: Expected {expected}, got {filename}")
                                        print()
                                else:
                                    print(f"   ❌ No B035370 entries found")
                            else:
                                print(f"   ❌ No HEAT_NO column found in Extracted Data")
                            
                            # Show first few entries regardless
                            print(f"\n   📋 First 3 entries (any heat number):")
                            for idx in range(min(3, len(df))):
                                row = df.iloc[idx]
                                plate_no = row.get('PLATE_NO', 'N/A')
                                heat_no = row.get('HEAT_NO', 'N/A')
                                test_cert = row.get('TEST_CERT_NO', 'N/A')
                                filename = row.get('Filename', 'N/A')
                                
                                print(f"      Entry {idx + 1}: {plate_no} | {heat_no} | {test_cert} | {filename}")
                
                finally:
                    # Clean up temp Excel file
                    try:
                        os.unlink(temp_excel_path)
                    except:
                        pass
        
        finally:
            # Clean up temp ZIP file
            try:
                os.unlink(temp_zip_path)
            except:
                pass
        
        return True
        
    except Exception as e:
        print(f"❌ Error during testing: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_dfipl_excel_generation()
    if success:
        print(f"\n🎉 Excel generation test completed!")
        print(f"The Excel file should now contain proper combination-based filenames!")
        print(f"Instead of 'DFIPL-WNEL-001-S1-3-9.pdf', it should show entries like:")
        print(f"  - 24LP0366A1_B035370_JSW-PCMD-717472719.pdf")
        print(f"  - 24LP0522A1_B035370_JSW-PCMD-717472719.pdf")
        print(f"  - etc.")
    else:
        print(f"\n❌ Excel generation test failed!")