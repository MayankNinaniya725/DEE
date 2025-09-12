import os
import sys
import django

# Setup Django
sys.path.append('/code')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'extractor_project.settings')
django.setup()

print("===== FIXING MODEL DEFINITION MISMATCH =====")

# Create a backup of the models/__init__.py file
os.system("cp /code/extractor/models/__init__.py /code/extractor/models/__init__.py.bak")
print("✅ Created backup at /code/extractor/models/__init__.py.bak")

# Read the current models/__init__.py content
with open('/code/extractor/models/__init__.py', 'r') as f:
    init_content = f.read()

# Extract the UploadedPDF model from the modular file
start_idx = init_content.find("class UploadedPDF")
end_idx = init_content.find("class", start_idx + 1)
if end_idx == -1:
    end_idx = len(init_content)
old_model_def = init_content[start_idx:end_idx]

# Read the model definition from models.py
with open('/code/extractor/models.py', 'r') as f:
    models_content = f.read()

# Extract the UploadedPDF model from models.py
start_idx = models_content.find("class UploadedPDF")
end_idx = models_content.find("class", start_idx + 1)
if end_idx == -1:
    end_idx = len(models_content)
new_model_def = models_content[start_idx:end_idx]

# Update the model definition in models/__init__.py
updated_init_content = init_content.replace(old_model_def, new_model_def)

# Write the updated content
with open('/code/extractor/models/__init__.py', 'w') as f:
    f.write(updated_init_content)

print("✅ Updated UploadedPDF model in /code/extractor/models/__init__.py")
print("✅ Added status field to the model definition")

# Now let's also update the process_pdf view to ensure it works correctly
with open('/code/extractor/views/core.py', 'r') as f:
    core_content = f.read()

# Find the create call
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

# Update only if we find the exact pattern
if old_create in core_content:
    updated_core_content = core_content.replace(old_create, new_create)
    
    # Remove the later status update since we're now setting it at creation
    old_status_update = """        task = process_pdf_file.delay(uploaded_pdf.id, vendor_config)
        uploaded_pdf.status = 'PROCESSING'
        uploaded_pdf.save()"""

    new_status_update = """        task = process_pdf_file.delay(uploaded_pdf.id, vendor_config)
        # Update to PROCESSING status
        uploaded_pdf.status = 'PROCESSING'
        uploaded_pdf.save()"""

    updated_core_content = updated_core_content.replace(old_status_update, new_status_update)
    
    # Save the updated content
    with open('/code/extractor/views/core.py', 'w') as f:
        f.write(updated_core_content)
    
    print("✅ Updated process_pdf view to set status during creation")
else:
    print("⚠️ Could not find the exact pattern in process_pdf view")
    print("   Manual check and update may be required")

print("\nFixes have been applied. Please restart the web container to apply changes.")
