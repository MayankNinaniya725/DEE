"""
This script generates the master_log.xlsx file in the logs directory from the extractor.log file.
It extracts page numbers and field data from log entries and saves them to a structured Excel file.
"""
import os
import re
import json
import pandas as pd
import logging
from datetime import datetime

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def generate_master_log():
    """
    Generate master_log.xlsx from extractor.log entries.
    """
    try:
        # Path to the log file
        log_path = os.path.join('logs', 'extractor.log')
        
        # Path for the output Excel file
        output_path = os.path.join('logs', 'master_log.xlsx')
        
        # Check if log file exists
        if not os.path.exists(log_path):
            logger.error(f"Log file not found: {log_path}")
            return False
        
        # Parse the log file to extract entries
        logger.info(f"Parsing log file: {log_path}")
        entries = []
        
        with open(log_path, 'r') as f:
            for line in f:
                # Look for saved entries in the log
                if '[✔] Saved:' in line:
                    # Try to find the log entry
                    match = re.search(r'log_entry = (\{.*\})', line)
                    if match:
                        try:
                            entry_data = json.loads(match.group(1).replace("'", '"'))
                            if 'Page' in entry_data:
                                entries.append({
                                    'PLATE_NO': entry_data.get('PLATE_NO', ''),
                                    'HEAT_NO': entry_data.get('HEAT_NO', ''),
                                    'TEST_CERT_NO': entry_data.get('TEST_CERT_NO', ''),
                                    'Page': entry_data['Page'],
                                    'Timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                                })
                        except Exception as e:
                            logger.warning(f"Error parsing log entry: {e}")
                            continue
        
        if not entries:
            logger.warning("No valid entries found in log file")
            return False
        
        # Create DataFrame from entries
        df = pd.DataFrame(entries)
        
        # Create logs directory if it doesn't exist
        os.makedirs('logs', exist_ok=True)
        
        # Save to Excel
        df.to_excel(output_path, index=False)
        logger.info(f"Successfully saved {len(entries)} entries to {output_path}")
        
        return True
    
    except Exception as e:
        logger.error(f"Error generating master log Excel: {str(e)}")
        return False

if __name__ == "__main__":
    print("Starting master log Excel generation...")
    if generate_master_log():
        print("✅ Successfully generated master_log.xlsx!")
    else:
        print("❌ Failed to generate master log Excel. Check the logs for details.")