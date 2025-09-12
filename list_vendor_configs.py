import os
import sys
import django

# Setup Django
sys.path.append('/code')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'extractor_project.settings')
django.setup()

# Import our functions
from django.conf import settings
from extractor.models import Vendor

# List vendor config details
def list_vendor_configs():
    print("Vendor Config Information")
    print("=" * 50)
    
    vendors = Vendor.objects.all()
    print(f"Found {vendors.count()} vendors in the database")
    
    for vendor in vendors:
        print(f"\nVendor: {vendor.name} (ID: {vendor.id})")
        
        if vendor.config_file:
            print(f"  Config file field value: {vendor.config_file.name}")
            print(f"  Config file URL: {vendor.config_file.url}")
            
            # Check full path in media
            full_path = os.path.join(settings.MEDIA_ROOT, vendor.config_file.name)
            print(f"  Full media path: {full_path}")
            print(f"  File exists at media path: {os.path.exists(full_path)}")
            
            # Check vendor configs dir
            vendor_config_path = os.path.join(settings.VENDOR_CONFIGS_DIR, vendor.config_file.name)
            print(f"  Vendor configs dir path: {vendor_config_path}")
            print(f"  File exists in vendor configs dir: {os.path.exists(vendor_config_path)}")
            
            # Check for the file in the extractor directory
            extractor_path = "/code/extractor/vendor_configs"
            extractor_file_path = os.path.join(extractor_path, os.path.basename(vendor.config_file.name))
            print(f"  Extractor configs path: {extractor_file_path}")
            print(f"  File exists in extractor configs: {os.path.exists(extractor_file_path)}")
        else:
            print(f"  No config file set for this vendor")
    
    # Print settings information
    print("\nSettings Information:")
    print(f"  MEDIA_ROOT: {settings.MEDIA_ROOT}")
    print(f"  VENDOR_CONFIGS_DIR: {settings.VENDOR_CONFIGS_DIR}")
    
    # List actual files in the vendor configs directories
    print("\nActual files in vendor_configs directories:")
    
    print("\n1. Files in /code/media/vendor_configs:")
    try:
        files = os.listdir("/code/media/vendor_configs")
        for file in files:
            print(f"  - {file}")
    except Exception as e:
        print(f"  Error listing directory: {str(e)}")
    
    print("\n2. Files in /code/extractor/vendor_configs:")
    try:
        files = os.listdir("/code/extractor/vendor_configs")
        for file in files:
            print(f"  - {file}")
    except Exception as e:
        print(f"  Error listing directory: {str(e)}")

if __name__ == "__main__":
    list_vendor_configs()
