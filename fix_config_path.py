"""
Fix for the vendor config path
"""
import os
import sys
import django
import re

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'extractor_project.settings')
django.setup()

def main():
    # Path to the core.py file
    core_path = "/code/extractor/views/core.py"
    
    # Check if the file exists
    if not os.path.exists(core_path):
        print(f"??? File not found: {core_path}")
        return False
    
    # Read the file
    with open(core_path, 'r') as f:
        content = f.read()
    
    # Fix the vendor config path
    vendor_config_section = r"(\s+# Load vendor config\s+)config_path = os\.path\.join\(settings\.VENDOR_CONFIGS_DIR, vendor\.config_file\.name\)"
    
    # Fix the path
    new_vendor_config = r"\1config_path = os.path.join(settings.BASE_DIR, 'extractor', 'vendor_configs', os.path.basename(vendor.config_file.name))"
    
    # Update the vendor config path
    new_content = re.sub(vendor_config_section, new_vendor_config, content, flags=re.DOTALL)
    
    if new_content == content:
        print("?????? No changes made - pattern not found")
        return False
    
    # Backup the original file
    backup_path = core_path + ".bak3"
    with open(backup_path, 'w') as f:
        f.write(content)
    print(f"??? Created backup at {backup_path}")
    
    # Write the updated content
    with open(core_path, 'w') as f:
        f.write(new_content)
    
    print(f"??? Updated {core_path}")
    print("Changes made:")
    print("- Fixed vendor config path")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
