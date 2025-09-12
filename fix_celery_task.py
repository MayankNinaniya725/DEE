"""
Fix for the process_pdf_file Celery task call
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
    
    # Before the Celery task call, we need to load vendor config
    pdf_create_section = r"(\s+uploaded_pdf = UploadedPDF\.objects\.create\([^)]+\)\s+)"
    celery_call_section = r"(\s+# Trigger extraction via Celery\s+task = process_pdf_file\.delay\(uploaded_pdf\.id)\)"
    
    # Add vendor config loading
    vendor_config_code = """
        # Load vendor config
        config_path = os.path.join(settings.VENDOR_CONFIGS_DIR, vendor.config_file.name)
        vendor_config = None
        try:
            from extractor.utils.config_loader import load_vendor_config
            vendor_config = load_vendor_config(config_path)
        except Exception as e:
            logger.error(f"Error loading vendor config: {str(e)}")
            return JsonResponse({'error': 'Error loading vendor config'}, status=500)
    """
    
    # Update Celery task call
    new_celery_call = r"\1, vendor_config)"
    
    # Insert vendor config loading
    new_content = re.sub(pdf_create_section, r"\1" + vendor_config_code, content, flags=re.DOTALL)
    
    # Update Celery task call
    new_content = re.sub(celery_call_section, new_celery_call, new_content, flags=re.DOTALL)
    
    if new_content == content:
        print("?????? No changes made - patterns not found")
        return False
    
    # Backup the original file
    backup_path = core_path + ".bak2"
    with open(backup_path, 'w') as f:
        f.write(content)
    print(f"??? Created backup at {backup_path}")
    
    # Write the updated content
    with open(core_path, 'w') as f:
        f.write(new_content)
    
    print(f"??? Updated {core_path}")
    print("Changes made:")
    print("- Added vendor config loading")
    print("- Updated Celery task call to include vendor_config parameter")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
