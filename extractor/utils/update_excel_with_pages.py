# update_excel_with_pages.py
import os
import pandas as pd
import logging
import re
from django.conf import settings
from django.utils import timezone
from openpyxl import load_workbook
from extractor.models import ExtractedData, UploadedPDF, Vendor
import json

logger = logging.getLogger('extractor')

def update_master_excel_with_pages():
    """
    Update the master Excel file with all data from the database,
    including correct page numbers from the extraction logs.
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
        
        # First, try to read extractor log file to get page numbers
        extractor_log_path = os.path.join(settings.BASE_DIR, 'logs', 'extractor.log')
        page_info = {}
        
        if os.path.exists(extractor_log_path):
            try:
                with open(extractor_log_path, 'r') as f:
                    log_content = f.read()
                    
                    # Find all log entries in the format "log_entry = {..."
                    log_pattern = r'log_entry = (\{.*?\})'
                    log_matches = re.findall(log_pattern, log_content, re.DOTALL)
                    
                    for match in log_matches:
                        try:
                            # Convert single quotes to double quotes for JSON
                            json_str = match.replace("'", '"')
                            entry = json.loads(json_str)
                            
                            # Create a key based on the field values
                            key = (
                                entry.get('PLATE_NO', ''),
                                entry.get('HEAT_NO', ''),
                                entry.get('TEST_CERT_NO', '')
                            )
                            
                            # Store the page number
                            if 'Page' in entry:
                                page_info[key] = entry['Page']
                        except:
                            continue
                logger.info(f"Found {len(page_info)} entries with page numbers in logs")
            except Exception as e:
                logger.error(f"Error reading log file: {str(e)}")
        
        # First, group all entries by PDF ID and collect all values
        for entry in extracted_entries:
            pdf_id = entry.pdf_id
            if pdf_id not in pdf_entries:
                pdf_entries[pdf_id] = {
                    'PLATE_NO': [],
                    'HEAT_NO': [],
                    'TEST_CERT_NO': []
                }
            
            # Store all values by field type
            if entry.field_key in ['PLATE_NO', 'HEAT_NO', 'TEST_CERT_NO']:
                pdf_entries[pdf_id][entry.field_key].append(entry.field_value)
        
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
                    
                    # Try to get page number from log data
                    page_number = 1  # Default to 1
                    
                    # Create key to match with log data
                    key = (plate_no, heat_no, test_cert_no)
                    if key in page_info:
                        page_number = page_info[key]
                    
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
        
        logger.info(f"Successfully updated master Excel file with {len(data_list)} entries, including page numbers")
        return True
        
    except Exception as e:
        logger.error(f"Error updating master Excel: {str(e)}", exc_info=True)
        return False

if __name__ == "__main__":
    # This allows the script to be run directly for testing
    import django
    django.setup()
    try:
        success = update_master_excel_with_pages()
        print("Excel file regenerated successfully with page numbers!" if success else "No data to regenerate Excel file.")
    except Exception as e:
        import traceback
        print(f"Error: {str(e)}")
        traceback.print_exc()
