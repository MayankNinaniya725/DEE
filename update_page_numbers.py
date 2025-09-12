"""
This script updates the page numbers in the database to reflect the actual pages in the PDF
where data was extracted from. It also regenerates the Excel file with the correct page numbers.
"""
import os
import re
import logging
import django
from datetime import datetime

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'extractor_project.settings')
django.setup()

# Import Django models after setting up Django
from extractor.models import ExtractedData, UploadedPDF
from extractor.utils.update_excel_new import update_master_excel

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def update_page_numbers_from_logs():
    """
    Parse the extractor log files to extract page numbers for each extracted entry,
    and update the database with the correct page numbers.
    """
    try:
        # Path to the log file
        log_path = os.path.join('logs', 'extractor.log')
        
        if not os.path.exists(log_path):
            logger.error(f"Log file not found: {log_path}")
            return False
        
        logger.info(f"Reading log file: {log_path}")
        
        # Parse the log file
        entries_with_page = {}
        
        # Read the log file
        with open(log_path, 'r', errors='ignore') as f:
            log_content = f.read()
        
        # Look for page processing entries
        page_patterns = [
            r"Processing page (\d+) in .*/([^/]+\.pdf)",  # Extract page number and filename
            r"Using OCR fallback for page (\d+) due to",  # OCR fallback page number
            r"No entries found with standard extraction, trying OCR for page (\d+)"  # OCR retry page number
        ]
        
        # Extract all page numbers mentioned in the logs
        page_mentions = []
        for pattern in page_patterns:
            matches = re.findall(pattern, log_content)
            page_mentions.extend(matches)
        
        logger.info(f"Found {len(page_mentions)} page mentions in logs")
        
        # Look for extraction entries with their field values
        extracted_patterns = {
            'PLATE_NO': r"\[✔\] Saved: ([^_]+)_[^_]+_[^\.]+\.pdf",
            'HEAT_NO': r"\[✔\] Saved: [^_]+_([^_]+)_[^\.]+\.pdf",
            'TEST_CERT_NO': r"\[✔\] Saved: [^_]+_[^_]+_([^\.]+)\.pdf"
        }
        
        extraction_values = {}
        
        # Extract all field values mentioned in saved entries
        for field, pattern in extracted_patterns.items():
            matches = re.findall(pattern, log_content)
            for match in matches:
                if match not in extraction_values:
                    extraction_values[match] = field
        
        logger.info(f"Found {len(extraction_values)} extracted values in logs")
        
        # Look for error and success processing messages to associate pages with values
        processing_entries = {}
        current_page = None
        current_pdf = None
        
        # Parse log line by line to associate page numbers with extracted values
        with open(log_path, 'r', errors='ignore') as f:
            for line in f:
                # Check if this line contains a page processing entry
                for pattern in page_patterns:
                    match = re.search(pattern, line)
                    if match:
                        if len(match.groups()) == 2:
                            current_page = int(match.group(1))
                            current_pdf = match.group(2)
                        else:
                            current_page = int(match.group(1))
                        break
                
                # Check if this line contains a saved entry
                saved_match = re.search(r"\[✔\] Saved: ([^\.]+)\.pdf", line)
                if saved_match and current_page is not None:
                    filename = saved_match.group(1)
                    parts = filename.split('_')
                    if len(parts) >= 3:
                        plate_no = parts[0]
                        heat_no = parts[1]
                        test_cert_no = parts[2]
                        
                        # Store page number for each field value
                        processing_entries[plate_no] = current_page
                        processing_entries[heat_no] = current_page
                        processing_entries[test_cert_no] = current_page
        
        logger.info(f"Associated {len(processing_entries)} values with page numbers")
        
        # Update the database with the page numbers
        update_count = 0
        
        # Get all extracted data entries
        all_entries = ExtractedData.objects.all()
        
        for entry in all_entries:
            # Check if we have a page number for this field value
            if entry.field_value in processing_entries:
                page_number = processing_entries[entry.field_value]
                
                # Update the entry with the correct page number
                if entry.page_number != page_number:
                    entry.page_number = page_number
                    entry.save()
                    update_count += 1
        
        logger.info(f"Updated {update_count} database entries with correct page numbers")
        
        # Regenerate the Excel file with the correct page numbers
        logger.info("Regenerating Excel file with corrected page numbers")
        if update_master_excel():
            logger.info("Successfully updated Excel file with correct page numbers")
        else:
            logger.error("Failed to update Excel file")
        
        return True
    
    except Exception as e:
        logger.error(f"Error updating page numbers: {str(e)}", exc_info=True)
        return False

if __name__ == "__main__":
    print("Starting page number update from logs...")
    if update_page_numbers_from_logs():
        print("✅ Successfully updated database and Excel file with correct page numbers!")
    else:
        print("❌ Failed to update page numbers. Check the logs for details.")
