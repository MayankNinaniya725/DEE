"""
Test script for the new PDF package download functionality.
This script tests the new endpoints and utility functions.
"""
import sys
import os
import django

# Add the project root to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'extractor_project.settings')
django.setup()

from extractor.utils.pdf_zip_utils import get_extracted_files_info, create_pdf_specific_package

def test_pdf_package_functionality():
    """Test the PDF package functionality with sample data."""
    
    print("Testing PDF Package Download Functionality")
    print("=" * 50)
    
    # Test 1: Get extracted files info for a sample PDF
    print("\nTest 1: Getting extracted files info")
    sample_pdf = "MTC-81-150[130322].pdf"  # Example filename
    info = get_extracted_files_info(sample_pdf)
    
    print(f"PDF: {sample_pdf}")
    print(f"Base filename: {info['base_filename']}")
    print(f"Directory exists: {info['exists']}")
    print(f"File count: {info['file_count']}")
    print(f"Total size: {info['total_size']} bytes")
    
    if info['exists'] and info['file_count'] > 0:
        print("Sample files:")
        for i, file_info in enumerate(info['files'][:5]):  # Show first 5 files
            print(f"  {i+1}. {file_info['name']} ({file_info['size']} bytes)")
        if info['file_count'] > 5:
            print(f"  ... and {info['file_count'] - 5} more files")
    
    # Test 2: Create package if files exist
    if info['exists'] and info['file_count'] > 0:
        print("\nTest 2: Creating ZIP package")
        success, result = create_pdf_specific_package(sample_pdf)
        
        if success:
            print(f"✓ ZIP package created successfully")
            print(f"  Buffer size: {len(result.getvalue())} bytes")
        else:
            print(f"✗ Failed to create package: {result}")
    else:
        print("\nTest 2: Skipped (no extracted files found)")
    
    # Test 3: List all extraction directories
    print("\nTest 3: Listing all extraction directories")
    from django.conf import settings
    
    media_root = os.path.abspath(settings.MEDIA_ROOT)
    extracted_dir = os.path.join(media_root, "extracted")
    
    if os.path.exists(extracted_dir):
        dirs = [d for d in os.listdir(extracted_dir) 
                if os.path.isdir(os.path.join(extracted_dir, d))]
        print(f"Found {len(dirs)} extraction directories:")
        for i, dir_name in enumerate(dirs[:10], 1):  # Show first 10
            dir_path = os.path.join(extracted_dir, dir_name)
            file_count = sum(len(files) for _, _, files in os.walk(dir_path))
            print(f"  {i}. {dir_name} ({file_count} files)")
        if len(dirs) > 10:
            print(f"  ... and {len(dirs) - 10} more directories")
    else:
        print("No extraction directory found")
    
    print("\nTesting complete!")
    print("\nNew endpoints available:")
    print("- GET /download/pdf-package/?input_pdf=filename.pdf")
    print("- GET /download/pdf-package/<pdf_id>/")
    print("- GET /api/extracted-files-status/?input_pdf=filename.pdf")
    print("- GET /api/extraction-directories/")

if __name__ == "__main__":
    test_pdf_package_functionality()