import os
import sys
import django

# Setup Django
sys.path.append('/code')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'extractor_project.settings')
django.setup()

# Import our functions
from django.conf import settings
import shutil

def fix_views_py():
    print("Fixing views.py...")
    
    # Path to the original views.py
    views_path = "/code/extractor/views.py"
    backup_path = "/code/extractor/views.py.bak4"
    
    # Create backup
    try:
        shutil.copy(views_path, backup_path)
        print(f"Created backup at {backup_path}")
    except Exception as e:
        print(f"Error creating backup: {str(e)}")
        return
    
    # Read the file
    with open(views_path, 'r') as f:
        content = f.read()
    
    # Make replacements
    replacements = [
        # Fix config path construction
        (
            "config_path = os.path.join(settings.VENDOR_CONFIGS_DIR, vendor.config_file.name)",
            "config_path = os.path.join(settings.MEDIA_ROOT, vendor.config_file.name)"
        ),
        # Add detailed error logging
        (
            "except Exception as e:\n                logger.error(f\"Error loading vendor config: {str(e)}\", exc_info=True)",
            "except Exception as e:\n                logger.error(f\"Error loading vendor config: {str(e)}\", exc_info=True)\n                logger.error(f\"Attempted config path: {config_path}\")\n                logger.error(f\"File exists: {os.path.exists(config_path) if config_path else False}\")"
        )
    ]
    
    # Apply replacements
    for old, new in replacements:
        if old in content:
            content = content.replace(old, new)
            print(f"✅ Applied replacement:\n{old}\n→\n{new}\n")
        else:
            print(f"❌ Could not find text to replace:\n{old}\n")
    
    # Write back the file
    with open(views_path, 'w') as f:
        f.write(content)
    
    print("views.py updated successfully!")

if __name__ == "__main__":
    fix_views_py()
