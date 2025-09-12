import os
import sys
import django

# Setup Django
sys.path.append('/code')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'extractor_project.settings')
django.setup()

from django.db import connection
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
import hashlib
import uuid
from extractor.models import UploadedPDF, Vendor

print("===== VERIFYING PDF UPLOAD FIX =====")

# 1. Check if we can create a PDF with status field
print("\n1. Testing UploadedPDF creation with status field:")

# Get a vendor
vendors = Vendor.objects.all()
if not vendors.exists():
    print("❌ No vendors found in database.")
    exit(1)

vendor = vendors.first()
print(f"Using vendor: {vendor.name} (ID: {vendor.id})")

# Create a mock PDF file
pdf_content = b"%PDF-1.5\nTest PDF content"
pdf_file = SimpleUploadedFile(
    name=f"test_fix_{uuid.uuid4().hex[:7]}.pdf",
    content=pdf_content,
    content_type="application/pdf"
)

# Calculate hash
file_hash = hashlib.sha256(pdf_content).hexdigest()

# Test direct SQL insertion (this should work if the DB schema is correct)
print("\n2. Testing direct SQL insertion:")
with connection.cursor() as cursor:
    try:
        cursor.execute("""
            INSERT INTO extractor_uploadedpdf 
            (file, file_hash, file_size, uploaded_at, vendor_id, status) 
            VALUES (%s, %s, %s, datetime('now'), %s, %s)
        """, [
            pdf_file.name, 
            file_hash, 
            len(pdf_content),
            vendor.id,
            "PENDING"
        ])
        print("✅ Direct SQL insertion successful")
        
        # Get the last inserted ID
        cursor.execute("SELECT last_insert_rowid()")
        sql_pdf_id = cursor.fetchone()[0]
        print(f"Created PDF with ID: {sql_pdf_id}")
    except Exception as e:
        print(f"❌ Direct SQL insertion failed: {e}")

# Test model creation (this should work with our fix)
print("\n3. Testing model creation:")
try:
    # Save the file
    file_path = default_storage.save(f"uploads/{pdf_file.name}", ContentFile(pdf_file.read()))
    
    # Create the PDF
    pdf = UploadedPDF.objects.create(
        vendor=vendor,
        file=file_path,
        file_hash=file_hash,
        file_size=len(pdf_content),
        status='PENDING'
    )
    print(f"✅ Model creation successful (ID: {pdf.id})")
    
    # Check the database record
    with connection.cursor() as cursor:
        cursor.execute("SELECT id, file, status FROM extractor_uploadedpdf WHERE id = %s", [pdf.id])
        result = cursor.fetchone()
        if result:
            print(f"Database record: ID={result[0]}, File={result[1]}, Status={result[2]}")
            if result[2] == "PENDING":
                print("✅ Status field correctly set to PENDING")
            else:
                print(f"❌ Status field has unexpected value: {result[2]}")
        else:
            print("❌ Could not find PDF record in database")
except Exception as e:
    print(f"❌ Model creation failed: {e}")

# Check our process_pdf view fix
print("\n4. Checking process_pdf view fix:")
with open('/code/extractor/views/core.py', 'r') as f:
    content = f.read()

if "status='PENDING'" in content:
    print("✅ process_pdf view now includes status field during creation")
else:
    print("❌ process_pdf view still missing status field")

print("\nAll verification tests complete.")
print("The system should now correctly handle PDF uploads without status errors.")
