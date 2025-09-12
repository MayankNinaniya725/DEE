"""
This script updates the page numbers in the master Excel file by extracting them from the log entries.
It reads the extract_multi_entries log file to find the correct page numbers for each entry.
"""
import os
import pandas as pd
import re
import json
import logging
from datetime import datetime

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def update_excel_with_pages():
    try:
        # Path to the master Excel file
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
        try:
            df = pd.read_excel(excel_path)
            logger.info(f"Successfully read Excel file with {len(df)} rows")
        except Exception as e:
            logger.error(f"Error reading Excel file: {e}")
            return False
        
        # Parse the log file to extract page numbers
        logger.info(f"Parsing log file: {log_path}")
        page_info = {}
        entry_count = 0
        
        with open(log_path, 'r') as f:
            for line in f:
                # Look for saved entries in the log
                if '[✔] Saved:' in line:
                    # Try to find the log entry before this line
                    match = re.search(r'log_entry = (\{.*\})', line)
                    if match:
                        try:
                            entry_data = json.loads(match.group(1).replace("'", '"'))
                            if 'Page' in entry_data:
                                # Use a combination of fields as key to match with Excel
                                key = (
                                    entry_data.get('PLATE_NO', ''),
                                    entry_data.get('HEAT_NO', ''),
                                    entry_data.get('TEST_CERT_NO', '')
                                )
                                page_info[key] = entry_data['Page']
                                entry_count += 1
                        except Exception as e:
                            continue
        
        logger.info(f"Found {entry_count} entries with page information in logs")
        
        # Update the Excel file with page numbers
        updated_count = 0
        for i, row in df.iterrows():
            key = (
                str(row.get('PLATE_NO', '')),
                str(row.get('HEAT_NO', '')),
                str(row.get('TEST_CERT_NO', ''))
            )
            if key in page_info:
                df.at[i, 'Page'] = page_info[key]
                updated_count += 1
        
        logger.info(f"Updated {updated_count} rows with correct page numbers")
        
        # Save the updated Excel file
        backup_name = f"master_backup_{datetime.now().strftime('%Y%m%d%H%M%S')}.xlsx"
        backup_path = os.path.join('media', 'backups', backup_name)
        
        # Create a backup of the original file
        try:
            df_original = pd.read_excel(excel_path)
            df_original.to_excel(backup_path, index=False)
            logger.info(f"Created backup of original Excel file: {backup_path}")
        except Exception as e:
            logger.warning(f"Could not create backup: {e}")
        
        # Save the updated file
        try:
            df.to_excel(excel_path, index=False)
            logger.info(f"Successfully saved updated Excel file with page numbers")
            return True
        except Exception as e:
            logger.error(f"Error saving Excel file: {e}")
            return False
    
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return False

if __name__ == "__main__":
    print("Starting Excel update process...")
    if update_excel_with_pages():
        print("✅ Successfully updated Excel file with correct page numbers!")
    else:
        print("❌ Failed to update Excel file. Check the logs for details.")
