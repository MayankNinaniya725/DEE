import os
import logging
import shutil
import tempfile
from pathlib import Path
import zipfile
import io

logger = logging.getLogger(__name__)

def file_exists_and_readable(file_path):
    """
    Checks if a file exists and is readable.
    Returns a tuple of (exists, readable, error_message)
    """
    try:
        if not file_path:
            return False, False, "File path is empty"
            
        if not os.path.exists(file_path):
            return False, False, f"File does not exist: {file_path}"
            
        if not os.path.isfile(file_path):
            return False, False, f"Path exists but is not a file: {file_path}"
            
        if not os.access(file_path, os.R_OK):
            return True, False, f"File exists but is not readable: {file_path}"
            
        # Try to open the file to confirm it's readable
        try:
            with open(file_path, 'rb') as f:
                # Read a small chunk to verify
                f.read(1024)
            return True, True, None
        except Exception as e:
            return True, False, f"File exists but cannot be read: {str(e)}"
            
    except Exception as e:
        return False, False, f"Error checking file: {str(e)}"

def safe_copy_file(src_path, dst_path, chunk_size=1024*1024):
    """
    Safely copy a file with error handling and chunking for large files.
    Returns a tuple of (success, error_message)
    """
    try:
        # Check if source file exists and is readable
        exists, readable, error = file_exists_and_readable(src_path)
        if not exists:
            return False, f"Source file does not exist: {error}"
        if not readable:
            return False, f"Source file is not readable: {error}"
            
        # Ensure destination directory exists
        dst_dir = os.path.dirname(dst_path)
        os.makedirs(dst_dir, exist_ok=True)
        
        # Copy file in chunks to handle large files
        with open(src_path, 'rb') as src_file:
            with open(dst_path, 'wb') as dst_file:
                while True:
                    chunk = src_file.read(chunk_size)
                    if not chunk:
                        break
                    dst_file.write(chunk)
                    
        # Verify the copy was successful
        if os.path.exists(dst_path):
            dest_size = os.path.getsize(dst_path)
            src_size = os.path.getsize(src_path)
            
            if dest_size != src_size:
                return False, f"File sizes don't match: src={src_size}, dst={dest_size}"
                
            return True, None
        else:
            return False, "Destination file doesn't exist after copy"
            
    except Exception as e:
        return False, f"Error copying file: {str(e)}"

def create_safe_temp_dir():
    """
    Creates a safe temporary directory with proper permissions.
    Returns the path to the directory.
    """
    try:
        temp_dir = tempfile.mkdtemp(prefix="pdf_extract_")
        os.chmod(temp_dir, 0o755)  # Ensure directory has proper permissions
        return temp_dir
    except Exception as e:
        logger.error(f"Failed to create temp directory: {str(e)}")
        raise

def safe_rmtree(path):
    """Safely remove a directory tree with error handling."""
    try:
        if os.path.exists(path):
            shutil.rmtree(path)
        return True, None
    except Exception as e:
        logger.error(f"Failed to remove directory {path}: {str(e)}")
        return False, str(e)

def create_zip_from_directory(directory_path, zip_buffer=None):
    """
    Creates a ZIP file from a directory with robust error handling.
    If zip_buffer is provided, writes to it; otherwise creates a new BytesIO buffer.
    Returns a tuple of (success, zip_buffer or error_message)
    """
    if zip_buffer is None:
        zip_buffer = io.BytesIO()
    
    try:
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(directory_path):
                for file in files:
                    file_path = os.path.join(root, file)
                    
                    # Verify file exists and is readable
                    exists, readable, error = file_exists_and_readable(file_path)
                    if not exists or not readable:
                        logger.warning(f"Skipping file in ZIP: {error}")
                        continue
                    
                    try:
                        arcname = os.path.relpath(file_path, directory_path)
                        zipf.write(file_path, arcname=arcname)
                    except Exception as e:
                        logger.warning(f"Error adding {file_path} to ZIP: {str(e)}")
                        # Continue with other files instead of failing completely
        
        zip_buffer.seek(0)
        return True, zip_buffer
    except Exception as e:
        return False, f"Error creating ZIP file: {str(e)}"
