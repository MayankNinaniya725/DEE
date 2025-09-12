import os
import pandas as pd
import logging
from datetime import datetime

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def fix_page_numbers_in_excel():
    """
    Updates the page numbers in the master Excel file to match the actual page numbers
    of extracted entries. This assigns unique page numbers based on the order of entries
    within each PDF file.
    """
    try:
        # Path to the Excel file
        excel_path = os.path.join('media', 'backups', 'master.xlsx')
        
        # Check if file exists
        if not os.path.exists(excel_path):
            logger.error(f"Excel file not found: {excel_path}")
            return False
            
        # Read the Excel file
        logger.info(f"Reading Excel file: {excel_path}")
        df = pd.read_excel(excel_path)
        logger.info(f"Found {len(df)} rows in Excel file")
        
        # Create a backup of the original file
        backup_path = os.path.join('media', 'backups', f"master_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx")
        df.to_excel(backup_path, index=False)
        logger.info(f"Created backup at {backup_path}")
        
        # Group by Source PDF and assign sequential page numbers to each group
        update_count = 0
        for source_pdf, group in df.groupby('Source PDF'):
            # Get all rows for this PDF
            indices = group.index.tolist()
            
            # Assign sequential page numbers (starting from 1)
            for i, idx in enumerate(indices, start=1):
                df.at[idx, 'Page'] = i
                update_count += 1
        
        logger.info(f"Updated {update_count} rows with sequential page numbers based on PDF source")
        
        # Save the updated Excel file
        df.to_excel(excel_path, index=False)
        logger.info(f"Saved updated Excel file to {excel_path}")
        
        return True
    
    except Exception as e:
        logger.error(f"Error updating page numbers: {str(e)}")
        return False

if __name__ == "__main__":
    print("Starting page number update...")
    success = fix_page_numbers_in_excel()
    if success:
        print("✅ Successfully updated page numbers in Excel file!")
    else:
        print("❌ Failed to update page numbers. Check the logs for details.")
