import os
import pandas as pd
import re
import json
import logging
from datetime import datetime

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def fix_page_numbers():
    """
    Updates the page numbers in the master Excel file by reading the page information from the logs.
    """
    try:
        # Path to the Excel file
        excel_path = os.path.join('media', 'backups', 'master.xlsx')
        
        # Path to the log file
        log_path = os.path.join('logs', 'extractor.log')
        
        # Check if files exist
        if not os.path.exists(excel_path):
            logger.error(f"Excel file not found: {excel_path}")
            return False
            
        if not os.path.exists(log_path):
            logger.error(f"Log file not found: {log_path}")
            return False
            
        # Read the Excel file
        logger.info(f"Reading Excel file: {excel_path}")
        df = pd.read_excel(excel_path)
        logger.info(f"Found {len(df)} rows in Excel file")
        
        # Create a backup of the original file
        backup_path = os.path.join('media', 'backups', f"master_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx")
        df.to_excel(backup_path, index=False)
        logger.info(f"Created backup at {backup_path}")
        
        # Parse the log file for page numbers
        logger.info(f"Reading log file: {log_path}")
        page_numbers = {}
        
        with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
            log_content = f.read()
        
        # Look for log entries with page information
        pattern = r'\[✔\] Saved: (.*?)\.pdf'
        filename_matches = re.findall(pattern, log_content)
        
        # Now look for the corresponding log entry line that contains the page number
        for filename in filename_matches:
            # Look for nearby log entry
            entry_pattern = r'log_entry = \{.*?"Filename": "' + re.escape(filename) + r'\.pdf".*?"Page": (\d+).*?\}'
            entry_match = re.search(entry_pattern, log_content, re.DOTALL)
            
            if entry_match:
                page_number = int(entry_match.group(1))
                page_numbers[f"{filename}.pdf"] = page_number
        
        logger.info(f"Found {len(page_numbers)} page numbers in logs")
        
        # Update the Excel file with page numbers
        update_count = 0
        for i, row in df.iterrows():
            filename = row.get('Filename', '')
            if filename in page_numbers:
                df.at[i, 'Page'] = page_numbers[filename]
                update_count += 1
        
        logger.info(f"Updated {update_count} rows with correct page numbers")
        
        # Save the updated Excel file
        df.to_excel(excel_path, index=False)
        logger.info(f"Saved updated Excel file to {excel_path}")
        
        return True
    
    except Exception as e:
        logger.error(f"Error updating page numbers: {str(e)}")
        return False

if __name__ == "__main__":
    print("Starting page number update...")
    success = fix_page_numbers()
    if success:
        print("✅ Successfully updated page numbers in Excel file!")
    else:
        print("❌ Failed to update page numbers. Check the logs for details.")
