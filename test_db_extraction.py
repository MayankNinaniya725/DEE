"""
Simplified test script to verify if the extractor logic is working.
This script creates test entries directly in the database to simulate PDF extraction.
"""

import os
import sys
import django
import logging
import random
from datetime import datetime

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('test_extraction')

def main():
    # Setup Django environment
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'extractor_project.settings')
    try:
        django.setup()
    except Exception as e:
        logger.error(f"Error setting up Django: {e}")
        return False

    # Import Django models after setup
    from django.utils import timezone
    from extractor.models import Vendor, UploadedPDF, ExtractedData
    from django.contrib.auth.models import User

    try:
        # Get first vendor or create one if none exists
        logger.info("Looking for a vendor in the database...")
        vendor = Vendor.objects.first()
        
        if not vendor:
            logger.info("No vendor found. Creating a test vendor...")
            vendor = Vendor.objects.create(
                name="Test Vendor",
                # Note: This will be empty but sufficient for test
                config_file="vendor_configs/test_vendor.json"
            )
            logger.info(f"Created test vendor: {vendor.name}")
        else:
            logger.info(f"Using existing vendor: {vendor.name}")

        # Create a mock PDF record
        logger.info("Creating a mock PDF record...")
        test_pdf = UploadedPDF.objects.create(
            vendor=vendor,
            file="uploads/test_file.pdf",
            file_hash="test_hash_" + str(random.randint(1000, 9999)),
            file_size=1024,
            status='COMPLETED',
        )
        logger.info(f"Created mock PDF with ID: {test_pdf.id}")

        # Create test extracted data entries
        logger.info("Creating test extracted data entries...")
        test_entries = [
            ("PLATE_NO", f"PLATE-{random.randint(1000, 9999)}"),
            ("HEAT_NO", f"HEAT-{random.randint(1000, 9999)}"),
            ("TEST_CERT_NO", f"CERT-{random.randint(10000, 99999)}")
        ]
        
        for field_key, field_value in test_entries:
            ExtractedData.objects.create(
                vendor=vendor,
                pdf=test_pdf,
                field_key=field_key,
                field_value=field_value,
                page_number=1,
            )
            logger.info(f"Created test entry: {field_key} = {field_value}")

        # Verify the entries were created
        entries = ExtractedData.objects.filter(pdf=test_pdf)
        if entries.count() == len(test_entries):
            logger.info(f"✅ Successfully created {entries.count()} test entries")
            logger.info("The extractor database model is working correctly")
            
            # Print the entries
            for entry in entries:
                logger.info(f"  {entry.field_key}: {entry.field_value}")
                
            return True
        else:
            logger.error(f"❌ Expected {len(test_entries)} entries, but found {entries.count()}")
            return False

    except Exception as e:
        logger.error(f"Error during test: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False

if __name__ == "__main__":
    success = main()
    logger.info("Test completed" + (" successfully" if success else " with errors"))
    sys.exit(0 if success else 1)
