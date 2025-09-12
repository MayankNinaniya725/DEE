import os
import sys
import django

# Setup Django
sys.path.append('/code')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'extractor_project.settings')
django.setup()

# Import our functions
from django.conf import settings
from extractor.utils.config_loader import load_vendor_config
from extractor.models import Vendor

# Test loading configs from all available vendors
def test_vendor_configs():
    print("Starting vendor config load test...")
    
    # Get all vendors
    vendors = Vendor.objects.all()
    print(f"Found {vendors.count()} vendors in the database")
    
    for vendor in vendors:
        print(f"\nTesting vendor: {vendor.name}")
        if not vendor.config_file:
            print(f"  ❌ No config file set for vendor {vendor.name}")
            continue
            
        # Use MEDIA_ROOT instead of VENDOR_CONFIGS_DIR
        config_path = os.path.join(settings.MEDIA_ROOT, vendor.config_file.name)
        print(f"  Config path: {config_path}")
        print(f"  File exists: {os.path.exists(config_path)}")
        
        try:
            config = load_vendor_config(config_path)
            print(f"  ✅ Successfully loaded config for {vendor.name}")
            print(f"  Config contents: {list(config.keys())}")
        except Exception as e:
            print(f"  ❌ Error loading config: {str(e)}")

if __name__ == "__main__":
    test_vendor_configs()
