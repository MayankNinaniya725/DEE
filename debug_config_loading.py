"""
Debug tool for vendor config loading
"""
import os
import sys
import django
import json

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'extractor_project.settings')
django.setup()

# Import models and migration modules
from django.conf import settings
from extractor.models import Vendor

def main():
    print("=== Debug Tool for Vendor Config Loading ===")
    
    # Check if vendor configs directory exists
    vendor_configs_dir = getattr(settings, 'VENDOR_CONFIGS_DIR', None)
    print(f"VENDOR_CONFIGS_DIR setting: {vendor_configs_dir}")
    
    # Check BASE_DIR
    base_dir = settings.BASE_DIR
    print(f"BASE_DIR setting: {base_dir}")
    
    # Check for vendor config files in different locations
    locations = [
        '/code/extractor/vendor_configs',
        '/code/media/vendor_configs',
        os.path.join(base_dir, 'extractor', 'vendor_configs'),
        vendor_configs_dir if vendor_configs_dir else ''
    ]
    
    for location in locations:
        if not location:
            continue
        
        print(f"\nChecking location: {location}")
        if os.path.exists(location):
            print(f"??? Directory exists")
            files = os.listdir(location)
            print(f"Files found: {', '.join(files) if files else 'None'}")
            
            # Try to load each JSON file
            for file in files:
                if file.endswith('.json'):
                    try:
                        with open(os.path.join(location, file), 'r') as f:
                            config = json.load(f)
                        print(f"??? Successfully loaded {file}: {config.keys()}")
                    except Exception as e:
                        print(f"??? Error loading {file}: {str(e)}")
        else:
            print(f"??? Directory does not exist")
    
    # Check vendor records
    print("\nChecking vendor records:")
    vendors = Vendor.objects.all()
    for vendor in vendors:
        print(f"Vendor: {vendor.name}")
        print(f"  Config file path: {vendor.config_file.name}")
        print(f"  Config file URL: {vendor.config_file.url}")
        
        # Try to locate the config file
        for location in locations:
            if not location:
                continue
            
            # Try with just the filename
            basename = os.path.basename(vendor.config_file.name)
            full_path = os.path.join(location, basename)
            
            if os.path.exists(full_path):
                print(f"  ??? Found at: {full_path}")
                try:
                    from extractor.utils.config_loader import load_vendor_config
                    config = load_vendor_config(full_path)
                    print(f"  ??? Successfully loaded with config_loader: {config.keys() if config else 'None'}")
                except Exception as e:
                    print(f"  ??? Error loading with config_loader: {str(e)}")
            else:
                print(f"  ??? Not found at: {full_path}")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
