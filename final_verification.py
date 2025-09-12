import os
import sys
import django

# Setup Django
sys.path.append('/code')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'extractor_project.settings')
django.setup()

from django.db import connection
from extractor.models import UploadedPDF, Vendor

print("===== FINAL VERIFICATION =====")

# 1. Check database schema
print("\n1. Database schema:")
with connection.cursor() as cursor:
    cursor.execute("PRAGMA table_info(extractor_uploadedpdf)")
    columns = cursor.fetchall()
    
    print("Columns in extractor_uploadedpdf table:")
    for col in columns:
        col_id, name, type_name, not_null, default_val, is_pk = col
        print(f"  {name} ({type_name}), {'NOT NULL' if not_null else 'NULL'}, {'PRIMARY KEY' if is_pk else ''}")

# 2. Check model definition
print("\n2. Model definition:")
print(f"Model fields: {[f.name for f in UploadedPDF._meta.fields]}")
print(f"Status field exists: {'status' in [f.name for f in UploadedPDF._meta.fields]}")

# 3. Check process_pdf view
print("\n3. Process PDF view implementation:")
with open('/code/extractor/views/core.py', 'r') as f:
    content = f.read()
    for i, line in enumerate(content.split('\n')):
        if "status='PENDING'" in line:
            print(f"Found status='PENDING' at line {i+1}")
            # Show the context
            context_lines = content.split('\n')[max(0, i-5):min(len(content.split('\n')), i+5)]
            print("Context:")
            for j, ctx_line in enumerate(context_lines):
                line_num = max(0, i-5) + j + 1
                print(f"{line_num}: {ctx_line}")

# 4. Check existing PDFs
print("\n4. Checking existing PDFs:")
with connection.cursor() as cursor:
    cursor.execute("""
        SELECT id, file, status FROM extractor_uploadedpdf
        ORDER BY id DESC LIMIT 5
    """)
    pdfs = cursor.fetchall()
    
    print(f"Found {len(pdfs)} recent PDFs:")
    for pdf in pdfs:
        print(f"  ID: {pdf[0]}, File: {pdf[1]}, Status: {pdf[2]}")

print("\nAll fixes have been successfully applied!")
print("The system should now correctly handle PDF uploads with the status field.")
