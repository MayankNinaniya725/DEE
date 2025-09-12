import os
import sys
import django

# Setup Django
sys.path.append('/code')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'extractor_project.settings')
django.setup()

from django.db import connection
from extractor.models import UploadedPDF

print("===== CHECKING MODEL DEFINITION =====")

# Check the database schema
print("\n1. Database schema for extractor_uploadedpdf table:")
with connection.cursor() as cursor:
    cursor.execute("PRAGMA table_info(extractor_uploadedpdf)")
    columns = cursor.fetchall()
    
    print("Columns defined in the database:")
    for col in columns:
        col_id, name, type_name, not_null, default_val, is_pk = col
        print(f"  {name} ({type_name}), {'NOT NULL' if not_null else 'NULL'}, {'PRIMARY KEY' if is_pk else ''}")

# Check the model definition
print("\n2. Model definition for UploadedPDF:")
print(f"Model fields: {[f.name for f in UploadedPDF._meta.fields]}")
print(f"Model attributes: {dir(UploadedPDF)}")

# Check the file where model is defined
print("\n3. Searching for model definition file:")
for path in ['/code/extractor/models/__init__.py', '/code/extractor/models.py']:
    if os.path.exists(path):
        print(f"Found model file: {path}")
        with open(path, 'r') as f:
            content = f.read()
            print(f"File content (first 300 chars): {content[:300]}...")
            
            # Look for UploadedPDF class
            if "class UploadedPDF" in content:
                start_idx = content.find("class UploadedPDF")
                end_idx = content.find("class", start_idx + 1)
                if end_idx == -1:
                    end_idx = len(content)
                model_def = content[start_idx:end_idx]
                print(f"\nUploadedPDF model definition:\n{model_def}")
            else:
                print("UploadedPDF class not found in this file")
    else:
        print(f"File not found: {path}")

# Look for other files that might define the model
print("\n4. Looking for other potential model files:")
os.system("find /code -type f -name '*.py' -exec grep -l 'class UploadedPDF' {} \\;")

print("\nAnalysis complete. We need to update the model definition to include the status field.")
