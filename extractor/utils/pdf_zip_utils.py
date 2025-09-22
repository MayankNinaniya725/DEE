import os
import io
import zipfile
import logging
from django.http import HttpResponse, StreamingHttpResponse as StreamingResponse
from django.conf import settings
from typing import Tuple, Optional, Dict, Any

logger = logging.getLogger(__name__)

def create_pdf_specific_package(input_pdf_filename: str) -> Tuple[bool, Any]:
    """
    Creates a ZIP package for extracted files of a specific input PDF.
    
    Args:
        input_pdf_filename: Original uploaded PDF filename
        
    Returns:
        Tuple of (success: bool, result: BytesIO buffer or error message)
    """
    try:
        # Get the base filename without extension
        base_filename = os.path.splitext(os.path.basename(input_pdf_filename))[0]
        
        # Path where extracted files are stored
        media_root = os.path.abspath(settings.MEDIA_ROOT)
        pdf_output_dir = os.path.join(media_root, "extracted", base_filename)
        
        logger.info(f"Creating package for {input_pdf_filename}, looking in: {pdf_output_dir}")
        
        if not os.path.exists(pdf_output_dir):
            return False, f"No extracted files found for {input_pdf_filename}"
        
        # Create in-memory ZIP
        zip_buffer = io.BytesIO()
        file_count = 0
        
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zipf:
            for root, _, files in os.walk(pdf_output_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    # Add to ZIP, keeping relative path
                    arcname = os.path.relpath(file_path, pdf_output_dir)
                    zipf.write(file_path, arcname)
                    file_count += 1
                    
                    logger.debug(f"Added to ZIP: {arcname}")
        
        if file_count == 0:
            return False, f"No files found in extracted folder for {input_pdf_filename}"
        
        zip_buffer.seek(0)
        
        logger.info(f"Successfully created ZIP for {input_pdf_filename} with {file_count} files")
        return True, zip_buffer
        
    except Exception as e:
        logger.exception(f"Error creating package for {input_pdf_filename}: {str(e)}")
        return False, f"Error creating package: {str(e)}"

def create_streaming_zip_response(zip_buffer: io.BytesIO, filename: str) -> HttpResponse:
    """
    Creates a streaming ZIP response for download.
    
    Args:
        zip_buffer: BytesIO buffer containing the ZIP data
        filename: Name for the downloaded file (without .zip extension)
        
    Returns:
        HttpResponse for streaming download
    """
    zip_filename = f"{filename}_extracted.zip"
    
    # Create streaming response
    response = HttpResponse(
        zip_buffer.getvalue(),
        content_type="application/zip"
    )
    
    # Set download headers
    response['Content-Disposition'] = f'attachment; filename="{zip_filename}"'
    response['Content-Length'] = len(zip_buffer.getvalue())
    response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response['Pragma'] = 'no-cache'
    response['Expires'] = '0'
    
    logger.info(f"Serving ZIP: {zip_filename}, Size: {len(zip_buffer.getvalue())} bytes")
    
    return response

def get_extracted_files_info(input_pdf_filename: str) -> Dict[str, Any]:
    """
    Gets information about extracted files for a given input PDF.
    
    Args:
        input_pdf_filename: Original uploaded PDF filename
        
    Returns:
        Dictionary with file count and directory info
    """
    try:
        base_filename = os.path.splitext(os.path.basename(input_pdf_filename))[0]
        media_root = os.path.abspath(settings.MEDIA_ROOT)
        pdf_output_dir = os.path.join(media_root, "extracted", base_filename)
        
        info = {
            'base_filename': base_filename,
            'output_directory': pdf_output_dir,
            'exists': os.path.exists(pdf_output_dir),
            'file_count': 0,
            'total_size': 0,
            'files': []
        }
        
        if info['exists']:
            for root, _, files in os.walk(pdf_output_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    file_size = os.path.getsize(file_path)
                    info['files'].append({
                        'name': file,
                        'path': file_path,
                        'size': file_size,
                        'relative_path': os.path.relpath(file_path, pdf_output_dir)
                    })
                    info['file_count'] += 1
                    info['total_size'] += file_size
        
        return info
        
    except Exception as e:
        logger.exception(f"Error getting file info for {input_pdf_filename}: {str(e)}")
        return {
            'base_filename': '',
            'output_directory': '',
            'exists': False,
            'file_count': 0,
            'total_size': 0,
            'files': [],
            'error': str(e)
        }