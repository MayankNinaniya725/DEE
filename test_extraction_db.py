"""
Simplified test script for testing extractor database functionality
"""

import os
import sys
import django
import logging
import random
import tempfile
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
    from django.core.files.base import ContentFile
    from extractor.models import Vendor, UploadedPDF, ExtractedData

    try:
        # Get first vendor or create one if none exists
        logger.info("Looking for a vendor in the database...")
        vendor = Vendor.objects.first()
        
        if not vendor:
            logger.info("No vendor found. Creating a test vendor...")
            
            # Create a test vendor config file
            config_content = """
            {
                "vendor_id": "test_vendor",
                "vendor_name": "Test Vendor",
                "fields": {
                    "PLATE_NO": "\\\\bT\\\\d{5}\\\\b",
                    "HEAT_NO": "\\\\bH\\\\d{5}\\\\b",
                    "TEST_CERT_NO": "\\\\bC\\\\d{5}\\\\b"
                }
            }
            """
            config_file = ContentFile(config_content.encode('utf-8'), name="test_vendor.json")
            
            vendor = Vendor.objects.create(
                name="Test Vendor",
                config_file=config_file
            )
            logger.info(f"Created test vendor: {vendor.name}")
        else:
            logger.info(f"Using existing vendor: {vendor.name}")

        # Create a mock PDF file
        logger.info("Creating a test PDF file...")
        pdf_content = b"%PDF-1.4\n1 0 obj\n<</Type/Catalog/Pages 2 0 R>>\nendobj\n2 0 obj\n<</Type/Pages/Kids[3 0 R]/Count 1>>\nendobj\n3 0 obj\n<</Type/Page/MediaBox[0 0 612 792]/Parent 2 0 R/Resources<<>>>>\nendobj\nxref\n0 4\n0000000000 65535 f\n0000000009 00000 n\n0000000058 00000 n\n0000000111 00000 n\ntrailer\n<</Size 4/Root 1 0 R>>\nstartxref\n190\n%%EOF"
        pdf_file = ContentFile(pdf_content, name=f"test_file_{random.randint(1000, 9999)}.pdf")
        
        # Create the PDF record
        logger.info("Creating a PDF database record...")
        test_pdf = UploadedPDF.objects.create(
            vendor=vendor,
            file=pdf_file,
            file_hash=f"test_hash_{random.randint(1000, 9999)}",
            file_size=len(pdf_content),
            status='COMPLETED'
        )
        logger.info(f"Created test PDF with ID: {test_pdf.id}")

        # Create test extracted data entries
        logger.info("Creating test extracted data entries...")
        test_entries = [
            ("PLATE_NO", f"T{random.randint(10000, 99999)}"),
            ("HEAT_NO", f"H{random.randint(10000, 99999)}"),
            ("TEST_CERT_NO", f"C{random.randint(10000, 99999)}")
        ]
        
        for field_key, field_value in test_entries:
            ExtractedData.objects.create(
                vendor=vendor,
                pdf=test_pdf,
                field_key=field_key,
                field_value=field_value,
                page_number=1
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
                
            # Check if entries show up in the admin (indirectly)
            logger.info("Checking if entries are properly linked to PDF...")
            pdf_entry_count = test_pdf.extracted_data.count()
            logger.info(f"PDF has {pdf_entry_count} linked extracted data entries")
            
            if pdf_entry_count == len(test_entries):
                logger.info("✅ PDF-to-Data relationship is working correctly")
            else:
                logger.warning(f"⚠️ Expected {len(test_entries)} linked entries, but found {pdf_entry_count}")
                
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
