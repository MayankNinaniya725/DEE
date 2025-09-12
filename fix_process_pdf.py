import os
import sys
import django

# Setup Django
sys.path.append('/code')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'extractor_project.settings')
django.setup()

print("===== FIXING PROCESS_PDF VIEW =====")

# Create a backup of the core.py file
os.system("cp /code/extractor/views/core.py /code/extractor/views/core.py.bak")
print("✅ Created backup at /code/extractor/views/core.py.bak")

# Read the current content
with open('/code/extractor/views/core.py', 'r') as f:
    content = f.read()

# Find the create call and add the status field
old_create = """        uploaded_pdf = UploadedPDF.objects.create(
            vendor=vendor,
            file=file_path,
            file_hash=file_hash,
            file_size=pdf_file.size,

        )"""

new_create = """        uploaded_pdf = UploadedPDF.objects.create(
            vendor=vendor,
            file=file_path,
            file_hash=file_hash,
            file_size=pdf_file.size,
            status='PENDING'
        )"""

# Replace the text
updated_content = content.replace(old_create, new_create)

# Remove the later status update since we're now setting it at creation
old_status_update = """        task = process_pdf_file.delay(uploaded_pdf.id, vendor_config)
        uploaded_pdf.status = 'PROCESSING'
        uploaded_pdf.save()"""

new_status_update = """        task = process_pdf_file.delay(uploaded_pdf.id, vendor_config)
        # Status is already set to PENDING during creation"""

updated_content = updated_content.replace(old_status_update, new_status_update)

# Write the updated content
with open('/code/extractor/views/core.py', 'w') as f:
    f.write(updated_content)

print("✅ Fixed process_pdf view by adding status field during creation")
print("✅ Updated process_pdf to use PENDING as initial status")

print("\nFixes have been applied. Please restart the web container to apply changes.")
