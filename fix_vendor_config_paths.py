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

def fix_vendor_config_paths():
    print("Starting vendor config path fix...")
    
    # Find all vendor configs
    all_configs = {}
    
    # Look in media/vendor_configs
    media_configs_path = "/code/media/vendor_configs"
    print(f"Checking for configs in {media_configs_path}")
    try:
        media_files = os.listdir(media_configs_path)
        for file in media_files:
            if file.endswith('.json'):
                all_configs[file] = os.path.join(media_configs_path, file)
                print(f"  Found {file} in media directory")
    except Exception as e:
        print(f"Error listing media configs directory: {str(e)}")
    
    # Look in extractor/vendor_configs
    extractor_configs_path = "/code/extractor/vendor_configs"
    print(f"Checking for configs in {extractor_configs_path}")
    try:
        extractor_files = os.listdir(extractor_configs_path)
        for file in extractor_files:
            if file.endswith('.json'):
                # Copy to media directory if not there
                if file not in all_configs:
                    all_configs[file] = os.path.join(extractor_configs_path, file)
                    print(f"  Found {file} in extractor directory only")
    except Exception as e:
        print(f"Error listing extractor configs directory: {str(e)}")
    
    # Copy all configs from extractor to media
    print("\nCopying missing configs from extractor to media...")
    for file, src_path in all_configs.items():
        if src_path.startswith(extractor_configs_path):
            dest_path = os.path.join(media_configs_path, file)
            if not os.path.exists(dest_path):
                try:
                    import shutil
                    shutil.copy(src_path, dest_path)
                    print(f"  ✅ Copied {file} from extractor to media directory")
                except Exception as e:
                    print(f"  ❌ Error copying {file}: {str(e)}")
    
    # Update vendor references
    print("\nUpdating vendor records...")
    vendors = Vendor.objects.all()
    for vendor in vendors:
        print(f"Checking vendor: {vendor.name}")
        
        if not vendor.config_file:
            print(f"  ❌ No config file set for vendor {vendor.name}")
            continue
            
        config_name = os.path.basename(vendor.config_file.name)
        print(f"  Config file basename: {config_name}")
        
        # Check if we need to update the path
        if vendor.config_file.name.startswith('vendor_configs/'):
            # The path is already correct format
            print(f"  ✓ Config path already has correct format: {vendor.config_file.name}")
            
            # Verify the file exists
            full_path = os.path.join(settings.MEDIA_ROOT, vendor.config_file.name)
            if not os.path.exists(full_path):
                # File doesn't exist, let's try to find it by basename
                if config_name in all_configs:
                    # Copy the file to the right location
                    try:
                        import shutil
                        os.makedirs(os.path.dirname(full_path), exist_ok=True)
                        shutil.copy(all_configs[config_name], full_path)
                        print(f"  ✅ Copied missing file to {full_path}")
                    except Exception as e:
                        print(f"  ❌ Error copying missing file: {str(e)}")
            else:
                print(f"  ✓ File exists at {full_path}")
        else:
            # Update to the correct format
            old_name = vendor.config_file.name
            new_name = f"vendor_configs/{config_name}"
            
            # Save the old name for reference
            vendor.config_file.name = new_name
            vendor.save()
            print(f"  ✅ Updated config path from {old_name} to {new_name}")

    print("\nFix completed!")

if __name__ == "__main__":
    fix_vendor_config_paths()
