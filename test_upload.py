"""
Script to test the PDF upload process
"""

import os
import sys
import django
import logging
import json
from io import BytesIO

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger('upload_test')

# Sample minimal PDF content
SAMPLE_PDF = b"%PDF-1.4\n1 0 obj\n<</Type/Catalog/Pages 2 0 R>>\nendobj\n2 0 obj\n<</Type/Pages/Kids[3 0 R]/Count 1>>\nendobj\n3 0 obj\n<</Type/Page/MediaBox[0 0 612 792]/Parent 2 0 R/Resources<<>>>>\nendobj\nxref\n0 4\n0000000000 65535 f\n0000000009 00000 n\n0000000058 00000 n\n0000000111 00000 n\ntrailer\n<</Size 4/Root 1 0 R>>\nstartxref\n190\n%%EOF"

def main():
    # Setup Django
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'extractor_project.settings')
    django.setup()
    
    # Import Django modules
    from django.core.files.uploadedfile import SimpleUploadedFile
    from django.test import Client
    from extractor.models import Vendor
    
    try:
        # Get first vendor
        vendor = Vendor.objects.first()
        if not vendor:
            logger.error("No vendor found in database. Please create one first.")
            return False
        
        logger.info(f"Testing upload with vendor: {vendor.name}")
        
        # Create test client
        client = Client()
        
        # Create test PDF file
        pdf_file = SimpleUploadedFile(
            name="test_upload.pdf",
            content=SAMPLE_PDF,
            content_type="application/pdf"
        )
        
        # Prepare form data
        form_data = {
            'vendor': vendor.id,
            'pdf': pdf_file
        }
        
        # Make the request to process-pdf endpoint
        logger.info("Sending test PDF upload request...")
        response = client.post('/process-pdf/', form_data)
        
        # Check response
        logger.info(f"Response status code: {response.status_code}")
        
        if response.status_code == 200:
            response_data = json.loads(response.content)
            logger.info(f"Response data: {response_data}")
            
            if 'redirect' in response_data:
                logger.info("??? Upload test PASSED! Received redirect response.")
                return True
            else:
                logger.warning(f"?????? Upload test returned 200 but unexpected response: {response_data}")
                return False
        else:
            logger.error(f"??? Upload test FAILED with status {response.status_code}")
            logger.error(f"Response content: {response.content}")
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
