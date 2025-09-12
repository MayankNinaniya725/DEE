"""
This script attempts to extract real page numbers from logs and update the Excel file.
It focuses on analyzing log entries to find the exact page number where each entry was extracted.
"""
import os
import re
import pandas as pd
import logging
from datetime import datetime

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def real_page_numbers_from_logs():
    """
    Extracts real page numbers from logs and updates the Excel file.
    """
    try:
        # Path to the Excel file
        excel_path = os.path.join('media', 'backups', 'master.xlsx')
        
        # Path to the log files
        log_folder = os.path.join('logs')
        
        # Check if files exist
        if not os.path.exists(excel_path):
            logger.error(f"Excel file not found: {excel_path}")
            return False
            
        if not os.path.exists(log_folder):
            logger.error(f"Log folder not found: {log_folder}")
            return False
            
        # Read the Excel file
        logger.info(f"Reading Excel file: {excel_path}")
        df = pd.read_excel(excel_path)
        logger.info(f"Found {len(df)} rows in Excel file")
        
        # Create a backup of the original file
        backup_path = os.path.join('media', 'backups', f"master_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx")
        df.to_excel(backup_path, index=False)
        logger.info(f"Created backup at {backup_path}")
        
        # Get a list of all log files
        log_files = []
        for file in os.listdir(log_folder):
            if file.endswith('.log'):
                log_files.append(os.path.join(log_folder, file))
        
        logger.info(f"Found {len(log_files)} log files")
        
        # Compile all log content
        log_content = ""
        for log_file in log_files:
            try:
                with open(log_file, 'r', errors='ignore') as f:
                    log_content += f.read() + "\n"
            except Exception as e:
                logger.error(f"Error reading log file {log_file}: {str(e)}")
        
        # Look for page processing and saved file patterns
        saved_file_pattern = r"\[✔\] Saved: ([^\.]+)\.pdf"
        page_pattern = r"Error processing page (\d+) in .*/([^/]+\.pdf)"
        ocr_pattern = r"OCR fallback for page (\d+)"
        
        saved_files = re.findall(saved_file_pattern, log_content)
        page_errors = re.findall(page_pattern, log_content)
        ocr_fallbacks = re.findall(ocr_pattern, log_content)
        
        logger.info(f"Found {len(saved_files)} saved files, {len(page_errors)} page errors, and {len(ocr_fallbacks)} OCR fallbacks")
        
        # Parse log line by line to find page number associated with each saved file
        page_info = {}
        current_page = None
        
        log_lines = log_content.split('\n')
        for i, line in enumerate(log_lines):
            # Check for page processing entries
            page_match = re.search(page_pattern, line)
            if page_match:
                current_page = int(page_match.group(1))
                continue
            
            # Check for OCR fallback entries
            ocr_match = re.search(ocr_pattern, line)
            if ocr_match:
                current_page = int(ocr_match.group(1))
                continue
            
            # Check for saved entries
            saved_match = re.search(saved_file_pattern, line)
            if saved_match and current_page is not None:
                filename = saved_match.group(1)
                parts = filename.split('_')
                
                if len(parts) >= 3:
                    plate_no = parts[0]
                    heat_no = parts[1]
                    test_cert_no = parts[2]
                    
                    # Store page number for each field value
                    page_info[plate_no] = current_page
                    page_info[heat_no] = current_page
                    page_info[test_cert_no] = current_page
        
        logger.info(f"Found {len(page_info)} values with page numbers from logs")
        
        # Update the Excel file with page numbers
        update_count = 0
        for i, row in df.iterrows():
            plate_no = str(row.get('PLATE_NO', ''))
            heat_no = str(row.get('HEAT_NO', ''))
            test_cert_no = str(row.get('TEST_CERT_NO', ''))
            
            # Try to find the page number for this row
            page_number = None
            
            if plate_no and plate_no in page_info:
                page_number = page_info[plate_no]
            elif heat_no and heat_no in page_info:
                page_number = page_info[heat_no]
            elif test_cert_no and test_cert_no in page_info:
                page_number = page_info[test_cert_no]
            
            # If we found a page number, update the row
            if page_number is not None:
                df.at[i, 'Page'] = page_number
                update_count += 1
        
        logger.info(f"Updated {update_count} rows with page numbers from logs")
        
        # If we didn't update many rows, keep the existing page numbers
        if update_count < 10:  # Very few updates
            logger.warning("Few page numbers found in logs, keeping existing page numbers")
        
        # Save the updated Excel file
        df.to_excel(excel_path, index=False)
        logger.info(f"Saved updated Excel file to {excel_path}")
        
        return True
    
    except Exception as e:
        logger.error(f"Error updating page numbers: {str(e)}")
        return False

if __name__ == "__main__":
    print("Starting page number extraction from logs...")
    success = real_page_numbers_from_logs()
    if success:
        print("✅ Successfully updated Excel file with real page numbers!")
    else:
        print("❌ Failed to update Excel file. Check the logs for details.")
