"""
This script generates the master_log.xlsx file by collecting extracted data
from the database and logs, ensuring proper page number tracking.
"""
import os
import django
import pandas as pd
import logging
from datetime import datetime

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'extractor_project.settings')
django.setup()

# Import Django models
from extractor.models import ExtractedData, UploadedPDF

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def generate_master_log():
    """
    Generate master_log.xlsx from database entries and log files.
    """
    try:
        # Get all PDFs with extracted data
        pdfs = UploadedPDF.objects.filter(extracted_data__isnull=False).distinct()
        
        if not pdfs:
            logger.warning("No PDFs with extracted data found in database")
            return False
        
        # Create a list to hold all data
        data_list = []
        
        # Process each PDF
        for pdf in pdfs:
            # Group entries by page
            entries_by_page = {}
            
            # Get all extracted data for this PDF
            entries = pdf.extracted_data.all().order_by('page_number')
            
            for entry in entries:
                page = entry.page_number
                if page not in entries_by_page:
                    entries_by_page[page] = {
                        'PLATE_NO': '',
                        'HEAT_NO': '',
                        'TEST_CERT_NO': '',
                        'Filename': os.path.basename(pdf.file.name),
                        'Page': page,
                        'Source PDF': pdf.file.name,
                        'Created': pdf.uploaded_at.strftime('%Y-%m-%d %H:%M:%S'),
                        'Hash': pdf.file_hash or '',
                        'Remarks': ''
                    }
                
                # Map the field values
                if entry.field_key == 'PLATE_NO':
                    entries_by_page[page]['PLATE_NO'] = entry.field_value
                elif entry.field_key == 'HEAT_NO':
                    entries_by_page[page]['HEAT_NO'] = entry.field_value
                elif entry.field_key == 'TEST_CERT_NO':
                    entries_by_page[page]['TEST_CERT_NO'] = entry.field_value
            
            # Add all entries to the data list
            data_list.extend(entries_by_page.values())
            except UploadedPDF.DoesNotExist:
                logger.warning(f"PDF with ID {entry.pdf_id} not found")
                continue
        
        if not data_list:
            logger.warning("No data rows created for Excel")
            return False
        
        # Create DataFrame
        df = pd.DataFrame(data_list)
        
        # Create logs directory if it doesn't exist
        os.makedirs('logs', exist_ok=True)
        
        # Save to Excel
        output_path = os.path.join('logs', 'master_log.xlsx')
        df.to_excel(output_path, index=False)
        
        logger.info(f"Successfully generated master_log.xlsx with {len(data_list)} entries")
        return True
        
    except Exception as e:
        logger.error(f"Error generating master log Excel: {str(e)}", exc_info=True)
        return False

if __name__ == "__main__":
    print("Starting master log Excel generation...")
    success = generate_master_log()
    if success:
        print("✅ Successfully generated master_log.xlsx!")
    else:
        print("❌ Failed to generate master log Excel. Check the logs for details.")