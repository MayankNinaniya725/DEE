import os
import io
import zipfile
import logging
import tempfile
from datetime import datetime
from django.http import HttpResponse, FileResponse
from django.conf import settings
from django.shortcuts import get_object_or_404
from extractor.models import UploadedPDF, ExtractedData
import pandas as pd

logger = logging.getLogger(__name__)

def create_download_package():
    """
    Creates a ZIP archive containing the master Excel file and all extracted PDFs.
    Returns a tuple of (success, result) where result is either the file buffer or an error message.
    """
    # Track success/failure stats
    stats = {
        'excel_included': False,
        'pdf_count': 0,
        'errors': []
    }
    
    # Create timestamp for unique filename
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    zip_filename = f"extraction_package_{timestamp}.zip"
    
    try:
        # Define paths - ensure they're absolute
        media_root = os.path.abspath(settings.MEDIA_ROOT)
        base_dir = os.path.abspath(settings.BASE_DIR)
        
        # Try multiple potential Excel file paths
        excel_paths = [
            os.path.join(media_root, "master_log.xlsx"),
            os.path.join(base_dir, "logs", "master_log.xlsx"),
            os.path.join(media_root, "logs", "master_log.xlsx"),
            os.path.join(media_root, "master.xlsx"),
            os.path.join(media_root, "all_extracted_data.xlsx")
        ]
        
        # Find first existing Excel file
        excel_file = None
        for path in excel_paths:
            if os.path.exists(path) and os.path.isfile(path):
                excel_file = path
                logger.info(f"Found Excel file at: {excel_file}")
                break
                
        if not excel_file:
            logger.warning(f"Excel file not found in any of the expected locations")
            excel_file = excel_paths[0]  # Default for error reporting
            
        pdf_dir = os.path.join(media_root, "extracted")
        
        logger.info(f"Creating ZIP package with Excel from: {excel_file}")
        logger.info(f"Looking for PDFs in: {pdf_dir}")
        
        # Create in-memory buffer
        buffer = io.BytesIO()
        
        with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
            # Add Excel if exists
            if excel_file and os.path.exists(excel_file) and os.path.isfile(excel_file):
                try:
                    # Test that we can actually read the file
                    with open(excel_file, 'rb') as f:
                        # Read a small chunk to verify
                        f.read(1024)
                    
                    # Add to ZIP with a clean arcname
                    arcname = os.path.basename(excel_file)
                    zip_file.write(excel_file, arcname=arcname)
                    stats['excel_included'] = True
                    logger.info(f"Excel file added to package successfully: {arcname}")
                except Exception as e:
                    error_msg = f"Error reading Excel file: {str(e)}"
                    stats['errors'].append(error_msg)
                    logger.error(error_msg)
            else:
                error_msg = f"Excel file not found at any of the expected locations"
                stats['errors'].append(error_msg)
                logger.warning(error_msg)

            # Add all PDFs if directory exists
            if os.path.exists(pdf_dir) and os.path.isdir(pdf_dir):
                pdf_count = 0
                
                # Walk through all subdirectories
                for root, dirs, files in os.walk(pdf_dir):
                    for filename in files:
                        if filename.lower().endswith('.pdf'):
                            pdf_path = os.path.join(root, filename)
                            try:
                                # Test that we can actually read the file
                                with open(pdf_path, 'rb') as f:
                                    # Read a small chunk to verify
                                    f.read(1024)
                                
                                # Calculate relative path for arcname to maintain directory structure
                                rel_path = os.path.relpath(pdf_path, media_root)
                                
                                # Add to ZIP with proper arcname
                                zip_file.write(pdf_path, arcname=rel_path)
                                pdf_count += 1
                                
                                if pdf_count % 100 == 0:  # Log progress for large collections
                                    logger.info(f"Added {pdf_count} PDFs to package so far...")
                                    
                            except Exception as e:
                                error_msg = f"Error reading PDF file {filename}: {str(e)}"
                                stats['errors'].append(error_msg)
                                logger.error(error_msg)
                
                stats['pdf_count'] = pdf_count
                logger.info(f"Added {pdf_count} PDFs to package")
            else:
                error_msg = f"PDF directory not found at: {pdf_dir}"
                stats['errors'].append(error_msg)
                logger.warning(error_msg)
        
        # Check if we have any content
        if not stats['excel_included'] and stats['pdf_count'] == 0:
            logger.error("No files were added to the ZIP package")
            return False, "No files found to include in the package. Please ensure the Excel file and PDFs exist."
        
        # Prepare response buffer
        buffer.seek(0)
        
        # Log success
        logger.info(f"ZIP package created successfully with {stats['pdf_count']} PDFs and Excel: {stats['excel_included']}")
        
        return True, (buffer, zip_filename, stats)
        
    except Exception as e:
        # Log the full error
        logger.exception(f"Error creating ZIP package: {str(e)}")
        return False, f"Error creating package: {str(e)}. Please contact support."

def create_package_response(request):
    """
    Creates a ZIP package and returns an appropriate HTTP response.
    """
    success, result = create_download_package()
    
    if not success:
        # Return error message
        return HttpResponse(
            result,
            content_type="text/plain", 
            status=404 if "not found" in result.lower() else 500
        )
    
    # Unpack the result
    buffer, zip_filename, stats = result
    
    # Use FileResponse for better handling of binary data
    response = FileResponse(
        buffer,
        as_attachment=True,
        filename=zip_filename
    )
    
    # Set additional headers for better browser compatibility
    response['Content-Type'] = 'application/zip'
    response['Content-Disposition'] = f'attachment; filename="{zip_filename}"'
    response['Content-Length'] = buffer.getbuffer().nbytes
    
    return response

def create_package_for_large_files():
    """
    Creates a ZIP archive for large files using temporary file instead of in-memory buffer.
    Returns a tuple of (success, result) where result is either the file path or an error message.
    """
    # Track success/failure stats
    stats = {
        'excel_included': False,
        'pdf_count': 0,
        'errors': []
    }
    
    # Create timestamp for unique filename
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    zip_filename = f"extraction_package_{timestamp}.zip"
    
    try:
        # Define paths - ensure they're absolute
        media_root = os.path.abspath(settings.MEDIA_ROOT)
        base_dir = os.path.abspath(settings.BASE_DIR)
        
        # Try multiple potential Excel file paths
        excel_paths = [
            os.path.join(media_root, "master_log.xlsx"),
            os.path.join(base_dir, "logs", "master_log.xlsx"),
            os.path.join(media_root, "logs", "master_log.xlsx"),
            os.path.join(media_root, "master.xlsx"),
            os.path.join(media_root, "all_extracted_data.xlsx")
        ]
        
        # Find first existing Excel file
        excel_file = None
        for path in excel_paths:
            if os.path.exists(path) and os.path.isfile(path):
                excel_file = path
                logger.info(f"Found Excel file at: {excel_file}")
                break
                
        if not excel_file:
            logger.warning(f"Excel file not found in any of the expected locations")
            excel_file = excel_paths[0]  # Default for error reporting
            
        pdf_dir = os.path.join(media_root, "extracted")
        
        logger.info(f"Creating large ZIP package with Excel from: {excel_file}")
        logger.info(f"Looking for PDFs in: {pdf_dir}")
        
        # Create a temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix='.zip') as tmp:
            tmp_path = tmp.name
        
        # Use the file for the ZIP
        with zipfile.ZipFile(tmp_path, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            # Add Excel if exists
            if excel_file and os.path.exists(excel_file) and os.path.isfile(excel_file):
                try:
                    arcname = os.path.basename(excel_file)
                    zip_file.write(excel_file, arcname=arcname)
                    stats['excel_included'] = True
                    logger.info(f"Excel file added to package successfully: {arcname}")
                except Exception as e:
                    error_msg = f"Error adding Excel file: {str(e)}"
                    stats['errors'].append(error_msg)
                    logger.error(error_msg)
            else:
                error_msg = f"Excel file not found at any of the expected locations"
                stats['errors'].append(error_msg)
                logger.warning(error_msg)
                
            # Add all PDFs if directory exists
            if os.path.exists(pdf_dir) and os.path.isdir(pdf_dir):
                pdf_count = 0
                
                # Walk through all subdirectories
                for root, dirs, files in os.walk(pdf_dir):
                    for filename in files:
                        if filename.lower().endswith('.pdf'):
                            pdf_path = os.path.join(root, filename)
                            try:
                                # Calculate relative path for arcname to maintain directory structure
                                rel_path = os.path.relpath(pdf_path, media_root)
                                
                                # Add to ZIP with proper arcname
                                zip_file.write(pdf_path, arcname=rel_path)
                                pdf_count += 1
                                
                                if pdf_count % 100 == 0:  # Log progress for large collections
                                    logger.info(f"Added {pdf_count} PDFs to package so far...")
                                    
                            except Exception as e:
                                error_msg = f"Error reading PDF file {filename}: {str(e)}"
                                stats['errors'].append(error_msg)
                                logger.error(error_msg)
                
                stats['pdf_count'] = pdf_count
                logger.info(f"Added {pdf_count} PDFs to package")
            else:
                error_msg = f"PDF directory not found at: {pdf_dir}"
                stats['errors'].append(error_msg)
                logger.warning(error_msg)
        
        # Check if we have any content
        if not stats['excel_included'] and stats['pdf_count'] == 0:
            # Clean up the temp file
            os.unlink(tmp_path)
            logger.error("No files were added to the ZIP package")
            return False, "No files found to include in the package. Please ensure the Excel file and PDFs exist."
        
        # Log success
        logger.info(f"Large ZIP package created successfully at {tmp_path} with {stats['pdf_count']} PDFs and Excel: {stats['excel_included']}")
        
        return True, (tmp_path, zip_filename, stats)
        
    except Exception as e:
        # Log the full error
        logger.exception(f"Error creating large ZIP package: {str(e)}")
        
        # Clean up the temp file if it exists
        if 'tmp_path' in locals():
            try:
                os.unlink(tmp_path)
            except:
                pass
                
        return False, f"Error creating package: {str(e)}. Please contact support."

def create_large_package_response(request):
    """
    Creates a large ZIP package using a temp file and returns an appropriate HTTP response.
    This is more suitable for large files than using an in-memory buffer.
    """
    success, result = create_package_for_large_files()
    
    if not success:
        # Return error message
        return HttpResponse(
            result,
            content_type="text/plain", 
            status=404 if "not found" in result.lower() else 500
        )
    
    # Unpack the result
    tmp_path, zip_filename, stats = result
    
    try:
        # Open the file and create a response
        with open(tmp_path, 'rb') as f:
            response = FileResponse(
                f,
                as_attachment=True,
                filename=zip_filename
            )
            
            # Set additional headers for better browser compatibility
            response['Content-Type'] = 'application/zip'
            response['Content-Disposition'] = f'attachment; filename="{zip_filename}"'
            
            # Get file size for Content-Length header
            file_size = os.path.getsize(tmp_path)
            response['Content-Length'] = file_size
            
            # The FileResponse will stream the file, and Django will clean up
            return response
    finally:
        # Ensure we clean up the temp file even if there's an exception
        try:
            os.unlink(tmp_path)
        except:
            logger.warning(f"Failed to remove temporary file: {tmp_path}")
    """
    Creates a ZIP archive containing the master Excel file and all extracted PDFs.
    Returns a tuple of (success, result) where result is either the file buffer or an error message.
    """
    # Track success/failure stats
    stats = {
        'excel_included': False,
        'pdf_count': 0,
        'errors': []
    }
    
    # Create timestamp for unique filename
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    zip_filename = f"extraction_package_{timestamp}.zip"
    
    try:
        # Define paths - ensure they're absolute
        media_root = os.path.abspath(settings.MEDIA_ROOT)
        excel_file = os.path.join(media_root, "master_log.xlsx")  # Updated to match your project's naming
        pdf_dir = os.path.join(media_root, "extracted")  # Updated to match your project's structure
        
        logger.info(f"Creating ZIP package with Excel from: {excel_file}")
        logger.info(f"Looking for PDFs in: {pdf_dir}")
        
        # Create in-memory buffer
        buffer = io.BytesIO()
        
        with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
            # Add Excel if exists
            if os.path.exists(excel_file) and os.path.isfile(excel_file):
                try:
                    # Test that we can actually read the file
                    with open(excel_file, 'rb') as f:
                        # Read a small chunk to verify
                        f.read(1024)
                    
                    # Add to ZIP with a clean arcname
                    zip_file.write(excel_file, arcname="master_log.xlsx")
                    stats['excel_included'] = True
                    logger.info("Excel file added to package successfully")
                except Exception as e:
                    error_msg = f"Error reading Excel file: {str(e)}"
                    stats['errors'].append(error_msg)
                    logger.error(error_msg)
            else:
                error_msg = f"Excel file not found at: {excel_file}"
                stats['errors'].append(error_msg)
                logger.warning(error_msg)

            # Add all PDFs if directory exists
            if os.path.exists(pdf_dir) and os.path.isdir(pdf_dir):
                pdf_count = 0
                
                # Walk through all subdirectories
                for root, dirs, files in os.walk(pdf_dir):
                    for filename in files:
                        if filename.lower().endswith('.pdf'):
                            pdf_path = os.path.join(root, filename)
                            try:
                                # Test that we can actually read the file
                                with open(pdf_path, 'rb') as f:
                                    # Read a small chunk to verify
                                    f.read(1024)
                                
                                # Calculate relative path for arcname to maintain directory structure
                                rel_path = os.path.relpath(pdf_path, media_root)
                                
                                # Add to ZIP with proper arcname
                                zip_file.write(pdf_path, arcname=rel_path)
                                pdf_count += 1
                                
                                if pdf_count % 100 == 0:  # Log progress for large collections
                                    logger.info(f"Added {pdf_count} PDFs to package so far...")
                                    
                            except Exception as e:
                                error_msg = f"Error reading PDF file {filename}: {str(e)}"
                                stats['errors'].append(error_msg)
                                logger.error(error_msg)
                
                stats['pdf_count'] = pdf_count
                logger.info(f"Added {pdf_count} PDFs to package")
            else:
                error_msg = f"PDF directory not found at: {pdf_dir}"
                stats['errors'].append(error_msg)
                logger.warning(error_msg)
        
        # Check if we have any content
        if not stats['excel_included'] and stats['pdf_count'] == 0:
            logger.error("No files were added to the ZIP package")
            return False, "No files found to include in the package. Please ensure the Excel file and PDFs exist."
        
        # Prepare response buffer
        buffer.seek(0)
        
        # Log success
        logger.info(f"ZIP package created successfully with {stats['pdf_count']} PDFs and Excel: {stats['excel_included']}")
        
        return True, (buffer, zip_filename, stats)
        
    except Exception as e:
        # Log the full error
        logger.exception(f"Error creating ZIP package: {str(e)}")
        return False, f"Error creating package: {str(e)}. Please contact support."

def create_package_response(request):
    """
    Creates a ZIP package and returns an appropriate HTTP response.
    """
    success, result = create_download_package()
    
    if not success:
        # Return error message
        return HttpResponse(
            result,
            content_type="text/plain", 
            status=404 if "not found" in result.lower() else 500
        )
    
    # Unpack the result
    buffer, zip_filename, stats = result
    
    # Use FileResponse for better handling of binary data
    response = FileResponse(
        buffer,
        as_attachment=True,
        filename=zip_filename
    )
    
    # Set additional headers for better browser compatibility
    response['Content-Type'] = 'application/zip'
    response['Content-Disposition'] = f'attachment; filename="{zip_filename}"'
    response['Content-Length'] = buffer.getbuffer().nbytes
    
    return response

def create_package_for_large_files():
    """
    Creates a ZIP archive for large files using temporary file instead of in-memory buffer.
    Returns a tuple of (success, result) where result is either the file path or an error message.
    """
    # Track success/failure stats
    stats = {
        'excel_included': False,
        'pdf_count': 0,
        'errors': []
    }
    
    # Create timestamp for unique filename
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    zip_filename = f"extraction_package_{timestamp}.zip"
    
    try:
        # Define paths - ensure they're absolute
        media_root = os.path.abspath(settings.MEDIA_ROOT)
        excel_file = os.path.join(media_root, "master_log.xlsx")
        pdf_dir = os.path.join(media_root, "extracted")
        
        logger.info(f"Creating large ZIP package with Excel from: {excel_file}")
        logger.info(f"Looking for PDFs in: {pdf_dir}")
        
        # Create a temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix='.zip') as tmp:
            tmp_path = tmp.name
        
        # Use the file for the ZIP
        with zipfile.ZipFile(tmp_path, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            # Add Excel if exists
            if os.path.exists(excel_file) and os.path.isfile(excel_file):
                try:
                    zip_file.write(excel_file, arcname="master_log.xlsx")
                    stats['excel_included'] = True
                except Exception as e:
                    error_msg = f"Error adding Excel file: {str(e)}"
                    stats['errors'].append(error_msg)
                    logger.error(error_msg)
            else:
                error_msg = f"Excel file not found at: {excel_file}"
                stats['errors'].append(error_msg)
                logger.warning(error_msg)
                
            # Add all PDFs if directory exists
            if os.path.exists(pdf_dir) and os.path.isdir(pdf_dir):
                pdf_count = 0
                
                # Walk through all subdirectories
                for root, dirs, files in os.walk(pdf_dir):
                    for filename in files:
                        if filename.lower().endswith('.pdf'):
                            pdf_path = os.path.join(root, filename)
                            try:
                                # Calculate relative path for arcname to maintain directory structure
                                rel_path = os.path.relpath(pdf_path, media_root)
                                
                                # Add to ZIP with proper arcname
                                zip_file.write(pdf_path, arcname=rel_path)
                                pdf_count += 1
                                
                                if pdf_count % 100 == 0:  # Log progress for large collections
                                    logger.info(f"Added {pdf_count} PDFs to package so far...")
                                    
                            except Exception as e:
                                error_msg = f"Error reading PDF file {filename}: {str(e)}"
                                stats['errors'].append(error_msg)
                                logger.error(error_msg)
                
                stats['pdf_count'] = pdf_count
                logger.info(f"Added {pdf_count} PDFs to package")
            else:
                error_msg = f"PDF directory not found at: {pdf_dir}"
                stats['errors'].append(error_msg)
                logger.warning(error_msg)
        
        # Check if we have any content
        if not stats['excel_included'] and stats['pdf_count'] == 0:
            # Clean up the temp file
            os.unlink(tmp_path)
            logger.error("No files were added to the ZIP package")
            return False, "No files found to include in the package. Please ensure the Excel file and PDFs exist."
        
        # Log success
        logger.info(f"Large ZIP package created successfully at {tmp_path} with {stats['pdf_count']} PDFs and Excel: {stats['excel_included']}")
        
        return True, (tmp_path, zip_filename, stats)
        
    except Exception as e:
        # Log the full error
        logger.exception(f"Error creating large ZIP package: {str(e)}")
        
        # Clean up the temp file if it exists
        if 'tmp_path' in locals():
            try:
                os.unlink(tmp_path)
            except:
                pass
                
        return False, f"Error creating package: {str(e)}. Please contact support."

def create_large_package_response(request):
    """
    Creates a large ZIP package using a temp file and returns an appropriate HTTP response.
    This is more suitable for large files than using an in-memory buffer.
    """
    success, result = create_package_for_large_files()
    
    if not success:
        # Return error message
        return HttpResponse(
            result,
            content_type="text/plain", 
            status=404 if "not found" in result.lower() else 500
        )
    
    # Unpack the result
    tmp_path, zip_filename, stats = result
    
    try:
        # Open the file and create a response
        with open(tmp_path, 'rb') as f:
            response = FileResponse(
                f,
                as_attachment=True,
                filename=zip_filename
            )
            
            # Set additional headers for better browser compatibility
            response['Content-Type'] = 'application/zip'
            response['Content-Disposition'] = f'attachment; filename="{zip_filename}"'
            
            # Get file size for Content-Length header
            file_size = os.path.getsize(tmp_path)
            response['Content-Length'] = file_size
            
            # The FileResponse will stream the file, and Django will clean up
            return response
    finally:
        # Ensure we clean up the temp file even if there's an exception
        try:
            os.unlink(tmp_path)
        except:
            logger.warning(f"Failed to remove temporary file: {tmp_path}")
