#!/usr/bin/env python
"""
Verification script for ZIP download functionality

This script provides a direct method to test the download_all_pdfs_package function
by simulating a request and examining the response.
"""
import os
import sys
import django
import logging
from io import BytesIO
import zipfile

# Set up Django environment
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'extractor_project.settings')
django.setup()

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Import Django components
from django.test import RequestFactory
from django.urls import reverse
from django.contrib.messages.storage.fallback import FallbackStorage

# Import the view to test
from extractor.views.downloads import download_all_pdfs_package

def verify_download_function():
    """
    Test the download_all_pdfs_package function directly
    """
    logger.info("Creating test request")
    factory = RequestFactory()
    request = factory.get(reverse('download_all_pdfs_package'))
    
    # Add message support to request
    setattr(request, 'session', 'session')
    messages = FallbackStorage(request)
    setattr(request, '_messages', messages)
    
    logger.info("Calling download_all_pdfs_package function")
    response = download_all_pdfs_package(request)
    
    logger.info(f"Response type: {type(response)}")
    logger.info(f"Response status code: {response.status_code if hasattr(response, 'status_code') else 'N/A'}")
    
    # Check if response is a redirect
    if hasattr(response, 'url'):
        logger.info(f"Response is a redirect to: {response.url}")
        return
    
    # Check if response is a file
    if hasattr(response, 'streaming_content'):
        logger.info("Response is a streaming response (FileResponse)")
        content = BytesIO()
        for chunk in response.streaming_content:
            content.write(chunk)
        
        content_size = content.tell()
        content.seek(0)
        logger.info(f"Response content size: {content_size} bytes")
        
        # Try to open as ZIP
        try:
            with zipfile.ZipFile(content) as zipf:
                file_list = zipf.namelist()
                logger.info(f"ZIP contains {len(file_list)} files:")
                for filename in file_list:
                    info = zipf.getinfo(filename)
                    logger.info(f"  - {filename} ({info.file_size} bytes)")
                
                # Check for key files
                excel_files = [f for f in file_list if f.endswith('.xlsx')]
                pdf_files = [f for f in file_list if f.endswith('.pdf')]
                logger.info(f"Found {len(excel_files)} Excel files and {len(pdf_files)} PDF files")
        except zipfile.BadZipFile:
            logger.error("Content is not a valid ZIP file")
            with open('invalid_zip.bin', 'wb') as f:
                f.write(content.getvalue())
            logger.info("Saved invalid content to 'invalid_zip.bin'")
    else:
        logger.info("Response is not a FileResponse")
        logger.info(f"Response headers: {getattr(response, 'headers', {})}")
        
        if hasattr(response, 'content'):
            content_length = len(response.content)
            logger.info(f"Response content length: {content_length} bytes")
            
            # Try to save the content for inspection
            with open('response_content.bin', 'wb') as f:
                f.write(response.content)
            logger.info("Saved response content to 'response_content.bin'")
            
            # Try to open as ZIP
            try:
                with zipfile.ZipFile(BytesIO(response.content)) as zipf:
                    file_list = zipf.namelist()
                    logger.info(f"ZIP contains {len(file_list)} files")
            except zipfile.BadZipFile:
                logger.error("Content is not a valid ZIP file")

if __name__ == "__main__":
    logger.info("Starting download verification")
    verify_download_function()
    logger.info("Verification complete")
