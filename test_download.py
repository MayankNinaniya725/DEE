#!/usr/bin/env python
"""
Test script for download_all_pdfs_package function

This script helps diagnose issues with ZIP file creation by running through
the same process as the view but in a more controlled environment.
"""
import os
import io
import sys
import django
import logging
import tempfile
import zipfile
from datetime import datetime

# Set up Django environment
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'extractor_project.settings')
django.setup()

# Import Django models after setting up the environment
from extractor.models import ExtractedData, UploadedPDF

# Configure logging to console
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('test_download')

def test_zip_file_creation():
    """
    Test function to simulate download_all_pdfs_package without HTTP context
    """
    # Set up tracking variables
    skipped_files = []
    pdf_success_count = 0
    
    try:
        # Step 1: Create temporary directory
        logger.info("Creating temporary directory")
        with tempfile.TemporaryDirectory() as temp_dir:
            logger.info(f"Created temporary directory: {temp_dir}")
            
            # Step 2: Query database for PDFs
            logger.info("Querying database for PDFs with extracted data")
            pdfs_with_data = UploadedPDF.objects.filter(
                extracted_data__isnull=False,
                status='COMPLETED'
            ).distinct()
            
            pdf_count = pdfs_with_data.count()
            logger.info(f"Found {pdf_count} PDFs with extracted data")
            
            if not pdfs_with_data.exists():
                logger.warning("No PDFs with extracted data found")
                return
            
            # Step 3: Create directory structure
            logger.info("Creating directory structure")
            package_dir = os.path.join(temp_dir, 'pdf_package')
            pdfs_dir = os.path.join(package_dir, 'pdfs')
            
            try:
                os.makedirs(pdfs_dir, exist_ok=True)
                logger.info(f"Created directories: {package_dir}, {pdfs_dir}")
            except Exception as e:
                logger.error(f"Failed to create directories: {str(e)}", exc_info=True)
                return
            
            # Step 4: Create a test file to verify filesystem
            test_file_path = os.path.join(package_dir, 'test.txt')
            try:
                with open(test_file_path, 'w') as f:
                    f.write('This is a test file to verify filesystem access.')
                logger.info(f"Created test file: {test_file_path}")
            except Exception as e:
                logger.error(f"Failed to create test file: {str(e)}", exc_info=True)
                # Continue despite test file failure
            
            # Step 5: Process first PDF for testing
            if pdf_count > 0:
                pdf = pdfs_with_data.first()
                logger.info(f"Testing with PDF ID={pdf.id}")
                
                # 5a: Validate the PDF file
                if not hasattr(pdf, 'file') or not pdf.file:
                    logger.error(f"PDF record {pdf.id} has no file attribute or it's None")
                    return
                
                pdf_filename = os.path.basename(pdf.file.name)
                logger.info(f"PDF filename: {pdf_filename}")
                pdf_dst_path = os.path.join(pdfs_dir, f"001_{pdf_filename}")
                
                # 5b: Check if file exists
                try:
                    pdf_src_path = pdf.file.path
                    logger.info(f"PDF source path: {pdf_src_path}")
                    
                    if not os.path.exists(pdf_src_path):
                        logger.error(f"PDF file not found: {pdf_src_path}")
                        return
                        
                    if not os.access(pdf_src_path, os.R_OK):
                        logger.error(f"PDF file not readable: {pdf_src_path}")
                        return
                    
                    # Get file size for debugging
                    file_size = os.path.getsize(pdf_src_path)
                    logger.info(f"PDF file size: {file_size} bytes")
                except Exception as e:
                    logger.error(f"Error validating PDF file: {str(e)}", exc_info=True)
                    return
                
                # 5c: Copy PDF file with buffered I/O
                try:
                    logger.info(f"Copying PDF from {pdf_src_path} to {pdf_dst_path}")
                    # Use buffered I/O with smaller chunks
                    with open(pdf_src_path, 'rb') as src_file:
                        with open(pdf_dst_path, 'wb') as dst_file:
                            # Copy in 1MB chunks
                            chunk_size = 1024 * 1024  # 1MB
                            while True:
                                chunk = src_file.read(chunk_size)
                                if not chunk:
                                    break
                                dst_file.write(chunk)
                    
                    # Verify the copy was successful
                    if os.path.exists(pdf_dst_path):
                        dest_size = os.path.getsize(pdf_dst_path)
                        logger.info(f"PDF copy successful: {dest_size} bytes")
                        pdf_success_count += 1
                    else:
                        logger.error(f"PDF copy failed: Destination file does not exist")
                        return
                    
                except Exception as e:
                    logger.error(f"Failed to copy PDF {pdf_src_path} to {pdf_dst_path}: {str(e)}", exc_info=True)
                    return
            
            # Step 6: Create a simple Excel test file
            try:
                import pandas as pd
                
                # Try a minimal Excel file first
                test_excel_path = os.path.join(package_dir, 'test.xlsx')
                logger.info(f"Creating test Excel file: {test_excel_path}")
                
                test_df = pd.DataFrame({'Test': ['This is a test']})
                test_df.to_excel(test_excel_path, index=False)
                
                if os.path.exists(test_excel_path):
                    excel_size = os.path.getsize(test_excel_path)
                    logger.info(f"Test Excel file created successfully: {excel_size} bytes")
                else:
                    logger.error("Test Excel file creation failed: file does not exist")
            except Exception as e:
                logger.error(f"Error creating test Excel file: {str(e)}", exc_info=True)
            
            # Step 7: Create a simple ZIP file
            try:
                # Create minimal test content for the ZIP
                test_zip_path = os.path.join(package_dir, 'test.zip')
                logger.info(f"Creating test ZIP file: {test_zip_path}")
                
                with zipfile.ZipFile(test_zip_path, 'w') as zipf:
                    zipf.writestr('test.txt', 'This is a test file in ZIP')
                
                if os.path.exists(test_zip_path):
                    zip_size = os.path.getsize(test_zip_path)
                    logger.info(f"Test ZIP file created successfully: {zip_size} bytes")
                else:
                    logger.error("Test ZIP file creation failed: file does not exist")
            except Exception as e:
                logger.error(f"Error creating test ZIP file: {str(e)}", exc_info=True)
            
            # Step 8: Try to create a ZIP file in memory
            try:
                # Create a memory buffer for ZIP
                zip_buffer = io.BytesIO()
                logger.info("Creating in-memory ZIP file")
                
                with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zipf:
                    # Add test files
                    if os.path.exists(test_file_path):
                        zipf.write(test_file_path, arcname='test.txt')
                        logger.info("Added test.txt to in-memory ZIP")
                    
                    if os.path.exists(test_excel_path):
                        zipf.write(test_excel_path, arcname='test.xlsx')
                        logger.info("Added test.xlsx to in-memory ZIP")
                    
                    # Try to add the PDF
                    if pdf_success_count > 0 and os.path.exists(pdf_dst_path):
                        zipf.write(pdf_dst_path, arcname=f'pdfs/001_{pdf_filename}')
                        logger.info(f"Added PDF to in-memory ZIP: {pdf_filename}")
                
                # Check if ZIP was created successfully
                zip_buffer.seek(0, os.SEEK_END)
                zip_size = zip_buffer.tell()
                zip_buffer.seek(0)
                
                if zip_size > 0:
                    logger.info(f"In-memory ZIP created successfully: {zip_size} bytes")
                    
                    # Write the in-memory ZIP to disk for testing
                    output_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'test_output.zip')
                    with open(output_path, 'wb') as f:
                        f.write(zip_buffer.getvalue())
                    logger.info(f"Saved in-memory ZIP to disk: {output_path}")
                else:
                    logger.error("In-memory ZIP creation failed: zero bytes")
                
            except Exception as e:
                logger.error(f"Error creating in-memory ZIP file: {str(e)}", exc_info=True)
            
    except Exception as e:
        logger.error(f"Error in test function: {str(e)}", exc_info=True)
    
    logger.info("Test completed")

if __name__ == "__main__":
    logger.info("Starting download test")
    test_zip_file_creation()
    logger.info("Test finished")
