# update_excel.py
import os
import pandas as pd
import logging
from django.conf import settings
from django.utils import timezone
from openpyxl import load_workbook
from extractor.models import ExtractedData, UploadedPDF, Vendor

logger = logging.getLogger('extractor')

def update_master_excel():
    """
    Update the master Excel file with all data from the database.
    This function creates or updates the master.xlsx file in MEDIA_ROOT/backups/
    """
    try:
        # Get all extracted data
        extracted_entries = ExtractedData.objects.all().order_by('created_at')
        
        if not extracted_entries:
            logger.warning("No extracted data found in database")
            return False
        
        # Create DataFrame from extracted data
        data_list = []
        
        # Group entries by PDF and field combinations
        pdf_entries = {}
        
        # First, group all entries by PDF ID and collect all values
        for entry in extracted_entries:
            pdf_id = entry.pdf_id
            if pdf_id not in pdf_entries:
                pdf_entries[pdf_id] = {
                    'PLATE_NO': [],
                    'HEAT_NO': [],
                    'TEST_CERT_NO': [],
                    'page_numbers': {}  # Store page numbers by field_key
                }
            
            # Store all values by field type
            if entry.field_key in ['PLATE_NO', 'HEAT_NO', 'TEST_CERT_NO']:
                pdf_entries[pdf_id][entry.field_key].append(entry.field_value)
                # Store the page number with the field_value as the key
                pdf_entries[pdf_id]['page_numbers'][f"{entry.field_key}_{entry.field_value}"] = entry.page_number
        
        # Get all PDFs that have extracted data
        pdf_ids = list(pdf_entries.keys())
        
        # Create rows for each PDF with all its entries
        sr_no = 1
        for pdf_id in pdf_ids:
            try:
                pdf = UploadedPDF.objects.get(id=pdf_id)
                vendor = pdf.vendor
                
                # Get all the data for this PDF
                pdf_data = pdf_entries[pdf_id]
                
                # Get the max number of entries for any field type
                max_entries = max(
                    len(pdf_data['PLATE_NO']),
                    len(pdf_data['HEAT_NO']),
                    len(pdf_data['TEST_CERT_NO'])
                )
                
                # If there are no entries at all, create one empty row
                if max_entries == 0:
                    row = {
                        'Sr No': sr_no,
                        'Vendor': vendor.name,
                        'PLATE_NO': '',
                        'HEAT_NO': '',
                        'TEST_CERT_NO': '',
                        'Filename': os.path.basename(pdf.file.name),
                        'Page': 1,
                        'Source PDF': pdf.file.name,
                        'Created': pdf.uploaded_at.strftime('%Y-%m-%d %H:%M:%S'),
                        'Hash': pdf.file_hash or '',
                        'Remarks': ''
                    }
                    data_list.append(row)
                    sr_no += 1
                    continue
                
                # For each entry in the max list, create a row
                for i in range(max_entries):
                    plate_no = pdf_data['PLATE_NO'][i] if i < len(pdf_data['PLATE_NO']) else ''
                    heat_no = pdf_data['HEAT_NO'][i] if i < len(pdf_data['HEAT_NO']) else ''
                    test_cert_no = pdf_data['TEST_CERT_NO'][i] if i < len(pdf_data['TEST_CERT_NO']) else ''
                    
                    # Get page numbers for the fields if available
                    page_number = 1  # Default to 1
                    
                    # Try to get page number from one of the fields, prioritizing PLATE_NO
                    if plate_no and f"PLATE_NO_{plate_no}" in pdf_data['page_numbers']:
                        page_number = pdf_data['page_numbers'][f"PLATE_NO_{plate_no}"]
                    elif heat_no and f"HEAT_NO_{heat_no}" in pdf_data['page_numbers']:
                        page_number = pdf_data['page_numbers'][f"HEAT_NO_{heat_no}"]
                    elif test_cert_no and f"TEST_CERT_NO_{test_cert_no}" in pdf_data['page_numbers']:
                        page_number = pdf_data['page_numbers'][f"TEST_CERT_NO_{test_cert_no}"]
                    
                    row = {
                        'Sr No': sr_no,
                        'Vendor': vendor.name,
                        'PLATE_NO': plate_no,
                        'HEAT_NO': heat_no,
                        'TEST_CERT_NO': test_cert_no,
                        'Filename': os.path.basename(pdf.file.name),
                        'Page': page_number,
                        'Source PDF': pdf.file.name,
                        'Created': pdf.uploaded_at.strftime('%Y-%m-%d %H:%M:%S'),
                        'Hash': pdf.file_hash or '',
                        'Remarks': ''
                    }
                    data_list.append(row)
                    sr_no += 1
                
            except UploadedPDF.DoesNotExist:
                logger.warning(f"PDF with ID {pdf_id} not found")
                continue
        
        if not data_list:
            logger.warning("No data rows created for Excel")
            return False
        
        # Create DataFrame
        df = pd.DataFrame(data_list)
        
        # Save to Excel
        backups_dir = os.path.join(settings.MEDIA_ROOT, "backups")
        os.makedirs(backups_dir, exist_ok=True)
        filename = os.path.join(backups_dir, "master.xlsx")
        sheet_name = timezone.localdate().isoformat()
        
        with pd.ExcelWriter(filename, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name=sheet_name, index=False)
        
        logger.info(f"Successfully updated master Excel file with {len(data_list)} entries")
        return True
        
    except Exception as e:
        logger.error(f"Error updating master Excel: {str(e)}", exc_info=True)
        return False

if __name__ == "__main__":
    # This allows the script to be run directly for testing
    import django
    django.setup()
    try:
        success = update_master_excel()
        print("Excel file regenerated successfully!" if success else "No data to regenerate Excel file.")
    except Exception as e:
        import traceback
        print(f"Error: {str(e)}")
        traceback.print_exc()
