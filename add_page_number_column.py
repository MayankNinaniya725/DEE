"""
This script manually updates the database schema to add a page_number column to the extractor_extracteddata table.
It uses direct SQL commands to modify the database, which is useful when you can't run Django migrations
due to configuration issues.

Before running this script, make sure you have configured the database connection parameters correctly.
"""

import os
import sys
import logging
import psycopg2
from datetime import datetime

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Database connection parameters - update these with your actual values
DB_PARAMS = {
    'dbname': 'your_db_name',
    'user': 'your_db_user',
    'password': 'your_db_password',
    'host': 'your_db_host',
    'port': 'your_db_port'
}

def add_page_number_column():
    """Add a page_number column to extractor_extracteddata table"""
    try:
        # Connect to the database
        logger.info("Connecting to database...")
        conn = psycopg2.connect(**DB_PARAMS)
        cursor = conn.cursor()
        
        # Check if the column already exists
        cursor.execute("""
            SELECT column_name FROM information_schema.columns 
            WHERE table_name = 'extractor_extracteddata' AND column_name = 'page_number';
        """)
        column_exists = cursor.fetchone() is not None
        
        if column_exists:
            logger.info("The page_number column already exists. No changes needed.")
            cursor.close()
            conn.close()
            return True
        
        # Add the column
        logger.info("Adding page_number column to extractor_extracteddata table...")
        cursor.execute("""
            ALTER TABLE extractor_extracteddata
            ADD COLUMN page_number INTEGER NOT NULL DEFAULT 1;
        """)
        conn.commit()
        
        # Update the page numbers based on the order of entries for each PDF
        logger.info("Updating page numbers for existing entries...")
        cursor.execute("""
            WITH entry_groups AS (
                SELECT 
                    id,
                    pdf_id,
                    ROW_NUMBER() OVER (PARTITION BY pdf_id ORDER BY created_at) as row_num
                FROM extractor_extracteddata
            )
            UPDATE extractor_extracteddata
            SET page_number = entry_groups.row_num
            FROM entry_groups
            WHERE extractor_extracteddata.id = entry_groups.id;
        """)
        conn.commit()
        
        # Get count of updated rows
        cursor.execute("SELECT COUNT(*) FROM extractor_extracteddata;")
        total_rows = cursor.fetchone()[0]
        
        logger.info(f"Successfully added page_number column and updated {total_rows} rows.")
        
        cursor.close()
        conn.close()
        return True
    
    except Exception as e:
        logger.error(f"Error updating database schema: {str(e)}")
        return False

if __name__ == "__main__":
    print("Starting database schema update...")
    if add_page_number_column():
        print("✅ Successfully added page_number column to the database!")
    else:
        print("❌ Failed to update database schema. Check the logs for details.")
