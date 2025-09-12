"""
This script updates the page numbers in the dashboard Excel file (master.xlsx) 
by copying them from the extraction log Excel file (master_log.xlsx).

This ensures that the dashboard displays the actual page numbers where each entry was extracted from.
"""
import os
import pandas as pd
import logging
from datetime import datetime

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def update_dashboard_with_log_page_numbers():
    """
    Update the dashboard Excel file with page numbers from the extraction log.
    """
    try:
        # Path to the dashboard Excel file
        dashboard_path = os.path.join('media', 'backups', 'master.xlsx')
        
        # Path to the extraction log Excel file
        log_path = os.path.join('logs', 'master_log.xlsx')
        
        # Check if files exist
        if not os.path.exists(dashboard_path):
            logger.error(f"Dashboard Excel file not found: {dashboard_path}")
            return False
            
        if not os.path.exists(log_path):
            logger.error(f"Extraction log Excel file not found: {log_path}")
            return False
            
        # Read the Excel files
        logger.info(f"Reading dashboard Excel file: {dashboard_path}")
        dashboard_df = pd.read_excel(dashboard_path)
        logger.info(f"Found {len(dashboard_df)} rows in dashboard Excel file")
        
        logger.info(f"Reading extraction log Excel file: {log_path}")
        log_df = pd.read_excel(log_path)
        logger.info(f"Found {len(log_df)} rows in extraction log Excel file")
        
        # Create a backup of the original dashboard file
        backup_path = os.path.join('media', 'backups', f"master_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx")
        dashboard_df.to_excel(backup_path, index=False)
        logger.info(f"Created backup at {backup_path}")
        
        # Create a mapping of field values to page numbers from the log file
        page_map = {}
        
        for _, row in log_df.iterrows():
            plate_no = str(row.get('PLATE_NO', ''))
            heat_no = str(row.get('HEAT_NO', ''))
            test_cert_no = str(row.get('TEST_CERT_NO', ''))
            page_number = row.get('Page', 1)
            
            if plate_no:
                page_map[plate_no] = page_number
            if heat_no:
                page_map[heat_no] = page_number
            if test_cert_no:
                page_map[test_cert_no] = page_number
        
        logger.info(f"Found {len(page_map)} values with page numbers in extraction log")
        
        # Update the dashboard with page numbers from the log
        update_count = 0
        
        for i, row in dashboard_df.iterrows():
            plate_no = str(row.get('PLATE_NO', ''))
            heat_no = str(row.get('HEAT_NO', ''))
            test_cert_no = str(row.get('TEST_CERT_NO', ''))
            
            # Try to find the page number for this row
            page_number = None
            
            if plate_no and plate_no in page_map:
                page_number = page_map[plate_no]
            elif heat_no and heat_no in page_map:
                page_number = page_map[heat_no]
            elif test_cert_no and test_cert_no in page_map:
                page_number = page_map[test_cert_no]
            
            # If we found a page number, update the row
            if page_number is not None:
                dashboard_df.at[i, 'Page'] = page_number
                update_count += 1
        
        logger.info(f"Updated {update_count} rows with page numbers from extraction log")
        
        # If we didn't update many rows, keep the existing page numbers
        if update_count < 10:  # Very few updates
            logger.warning("Few page numbers found in extraction log, keeping existing page numbers")
        
        # Save the updated dashboard Excel file
        dashboard_df.to_excel(dashboard_path, index=False)
        logger.info(f"Saved updated dashboard Excel file to {dashboard_path}")
        
        return True
    
    except Exception as e:
        logger.error(f"Error updating dashboard with log page numbers: {str(e)}")
        return False

if __name__ == "__main__":
    print("Starting update of dashboard page numbers from extraction log...")
    success = update_dashboard_with_log_page_numbers()
    if success:
        print("✅ Successfully updated dashboard with real page numbers from extraction log!")
    else:
        print("❌ Failed to update dashboard. Check the logs for details.")
