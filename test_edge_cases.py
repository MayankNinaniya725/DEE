#!/usr/bin/env python
"""
Test script for download_all_pdfs_package edge cases

This script tests the download function under simulated error conditions
to verify the robustness of the implementation.
"""
import os
import sys
import django
import logging
import tempfile
from unittest.mock import patch, MagicMock
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

def test_excel_failure():
    """
    Test the function when Excel creation fails
    """
    logger.info("=== Testing with Excel Failure ===")
    factory = RequestFactory()
    request = factory.get(reverse('download_all_pdfs_package'))
    
    # Add message support to request
    setattr(request, 'session', 'session')
    messages = FallbackStorage(request)
    setattr(request, '_messages', messages)
    
    # Patch pandas to simulate Excel creation failure
    with patch('pandas.DataFrame.to_excel') as mock_to_excel:
        # Make to_excel raise an exception
        mock_to_excel.side_effect = Exception("Simulated Excel creation failure")
        
        # Call the view
        logger.info("Calling download_all_pdfs_package with simulated Excel failure")
        response = download_all_pdfs_package(request)
        
        # Check response
        logger.info(f"Response type: {type(response)}")
        if hasattr(response, 'streaming_content'):
            logger.info("Function returned a streaming response despite Excel failure")
            
            # Extract content
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
                        logger.info(f"  - {filename}")
                    
                    # Check for fallback files
                    csv_files = [f for f in file_list if f.endswith('.csv')]
                    txt_files = [f for f in file_list if f.endswith('.txt')]
                    logger.info(f"Found {len(csv_files)} CSV files and {len(txt_files)} TXT files")
                    
                    # Excel files should not be present
                    excel_files = [f for f in file_list if f.endswith('.xlsx')]
                    if not excel_files:
                        logger.info("SUCCESS: No Excel files in the ZIP, as expected")
                    else:
                        logger.warning(f"UNEXPECTED: Found Excel files despite simulated failure: {excel_files}")
                    
                    # Should find fallback text files
                    if txt_files:
                        logger.info(f"SUCCESS: Found text fallback files: {txt_files}")
                    else:
                        logger.warning("FAIL: No text fallback files found")
                        
            except zipfile.BadZipFile:
                logger.error("Content is not a valid ZIP file")
        else:
            logger.info("Function did not return a streaming response")
            if hasattr(response, 'url'):
                logger.info(f"Response redirected to: {response.url}")

def test_missing_pdf_files():
    """
    Test the function when PDF files are missing
    """
    logger.info("=== Testing with Missing PDF Files ===")
    factory = RequestFactory()
    request = factory.get(reverse('download_all_pdfs_package'))
    
    # Add message support to request
    setattr(request, 'session', 'session')
    messages = FallbackStorage(request)
    setattr(request, '_messages', messages)
    
    # Patch os.path.exists to simulate missing PDF files
    with patch('os.path.exists') as mock_exists:
        # Make exists return False for PDF files but True for directories
        def side_effect(path):
            if path.endswith('.pdf'):
                return False
            return True
            
        mock_exists.side_effect = side_effect
        
        # Call the view
        logger.info("Calling download_all_pdfs_package with simulated missing PDF files")
        response = download_all_pdfs_package(request)
        
        # Check response
        logger.info(f"Response type: {type(response)}")
        if hasattr(response, 'url'):
            logger.info(f"SUCCESS: Function redirected to {response.url} as expected")
        else:
            logger.info("Function did not redirect as expected")
            
            # If it returned a ZIP file, it should only contain Excel without PDFs
            if hasattr(response, 'streaming_content'):
                logger.info("Function returned a streaming response despite missing PDFs")
                
                # Extract content
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
                            logger.info(f"  - {filename}")
                        
                        # No PDF files should be present
                        pdf_files = [f for f in file_list if f.endswith('.pdf')]
                        if not pdf_files:
                            logger.info("SUCCESS: No PDF files in the ZIP, as expected")
                        else:
                            logger.warning(f"UNEXPECTED: Found PDF files despite simulated missing files: {pdf_files}")
                            
                except zipfile.BadZipFile:
                    logger.error("Content is not a valid ZIP file")

if __name__ == "__main__":
    logger.info("Starting edge case tests")
    test_excel_failure()
    test_missing_pdf_files()
    logger.info("Edge case tests completed")
