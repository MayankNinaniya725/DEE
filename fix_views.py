"""
Fix for the process_pdf view to handle status field correctly
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
    
    # Locate the UploadedPDF.objects.create section
    pdf_create_pattern = r"(\s+uploaded_pdf = UploadedPDF\.objects\.create\(\s+.*?file_size=.*?,\s+)status='PROCESSING'(\s+\))"
    
    # Option 1: Remove the status field
    new_content = re.sub(pdf_create_pattern, r"\1\2", content, flags=re.DOTALL)
    
    if new_content == content:
        print("?????? No changes made - pattern not found")
        return False
    
    # Backup the original file
    backup_path = core_path + ".bak"
    with open(backup_path, 'w') as f:
        f.write(content)
    print(f"??? Created backup at {backup_path}")
    
    # Write the updated content
    with open(core_path, 'w') as f:
        f.write(new_content)
    
    print(f"??? Updated {core_path}")
    print("Changes made:")
    print("- Removed 'status' field from UploadedPDF.objects.create call")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
