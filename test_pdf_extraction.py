import os
import sys
import django
import time
from io import BytesIO
import json

# Setup Django
sys.path.append('/code')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'extractor_project.settings')
django.setup()

# Import our models
from django.conf import settings
from extractor.models import Vendor, UploadedPDF, ExtractedData
from extractor.utils.config_loader import load_vendor_config
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile

User = get_user_model()

def test_pdf_extraction():
    print("Starting PDF extraction test...")
    
    # 1. Check vendors
    vendors = Vendor.objects.all()
    if not vendors.exists():
        print("❌ No vendors found in the database. Please create a vendor first.")
        return
    
    vendor = vendors.first()
    print(f"Using vendor: {vendor.name} (ID: {vendor.id})")
    
    # 2. Load vendor config
    try:
        config_path = os.path.join(settings.MEDIA_ROOT, vendor.config_file.name)
        vendor_config = load_vendor_config(config_path)
        print(f"✅ Successfully loaded vendor config: {list(vendor_config.keys())}")
    except Exception as e:
        print(f"❌ Error loading vendor config: {str(e)}")
        return
    
    # 3. Find a test PDF
    test_pdf_path = None
    
    # Look in media/uploads
    uploads_dir = os.path.join(settings.MEDIA_ROOT, 'uploads')
    if os.path.exists(uploads_dir):
        for filename in os.listdir(uploads_dir):
            if filename.lower().endswith('.pdf'):
                test_pdf_path = os.path.join(uploads_dir, filename)
                break
    
    # If not found, check in media root
    if not test_pdf_path:
        for filename in os.listdir(settings.MEDIA_ROOT):
            if filename.lower().endswith('.pdf'):
                test_pdf_path = os.path.join(settings.MEDIA_ROOT, filename)
                break
    
    # If still not found, try looking in vendor_configs directory
    if not test_pdf_path:
        vendor_configs_dir = os.path.join(settings.MEDIA_ROOT, 'vendor_configs')
        if os.path.exists(vendor_configs_dir):
            for filename in os.listdir(vendor_configs_dir):
                if filename.lower().endswith('.pdf'):
                    test_pdf_path = os.path.join(vendor_configs_dir, filename)
                    break
    
    if not test_pdf_path:
        print("❌ No test PDF found. Please upload a PDF file to test extraction.")
        return
    
    print(f"Found test PDF: {test_pdf_path}")
    
    # 4. Create a user if none exists
    username = 'testuser'
    try:
        user = User.objects.get(username=username)
        print(f"Using existing user: {user.username}")
    except User.DoesNotExist:
        user = User.objects.create_user(username=username, password='testpassword', email='test@example.com')
        print(f"Created test user: {user.username}")
    
    # 5. Create an UploadedPDF object
    with open(test_pdf_path, 'rb') as f:
        pdf_content = f.read()
    
    from django.core.files.base import ContentFile
    
    # Calculate a simple hash for the file
    import hashlib
    file_hash = hashlib.md5(pdf_content).hexdigest()
    
    # Check if this PDF already exists
    existing_pdf = UploadedPDF.objects.filter(file_hash=file_hash).first()
    if existing_pdf:
        print(f"Using existing PDF: {existing_pdf.file.name} (ID: {existing_pdf.id})")
        pdf = existing_pdf
    else:
        # Create a filename
        filename = os.path.basename(test_pdf_path)
        
        # Create the PDF object
        pdf_file = SimpleUploadedFile(filename, pdf_content, content_type="application/pdf")
        
        # Use direct SQL to create the PDF record with status
        from django.db import connection
        with connection.cursor() as cursor:
            # Create record without status first
            sql = """
            INSERT INTO extractor_uploadedpdf 
            (file, vendor_id, file_hash, file_size, uploaded_at, status) 
            VALUES (?, ?, ?, ?, datetime('now'), 'PROCESSING')
            """
            cursor.execute(sql, [
                f"uploads/{filename}",
                vendor.id,
                file_hash,
                len(pdf_content)
            ])
            
            # Get the ID of the inserted record
            cursor.execute("SELECT last_insert_rowid()")
            pdf_id = cursor.fetchone()[0]
            
        # Now get the PDF object
        pdf = UploadedPDF.objects.get(id=pdf_id)
        print(f"Created new PDF record: {pdf.file.name} (ID: {pdf.id})")
    
    # 6. Call extraction directly using the celery task
    from extractor.tasks import process_pdf_file
    
    print("\nStarting PDF extraction task...")
    task = process_pdf_file.delay(pdf.id, vendor_config)
    print(f"Task ID: {task.id}")
    
    # 7. Wait for task to complete
    print("\nWaiting for extraction to complete...")
    for i in range(30):  # Wait up to 30 seconds
        time.sleep(1)
        pdf.refresh_from_db()
        
        # Use direct SQL to get the status
        from django.db import connection
        with connection.cursor() as cursor:
            cursor.execute(f"SELECT status FROM extractor_uploadedpdf WHERE id = {pdf.id};")
            status = cursor.fetchone()[0]
        
        status_emoji = "✅" if status == "COMPLETED" else "⏳" if status == "PROCESSING" else "❌"
        print(f"Status: {status_emoji} {status} (waited {i+1}s)")
        
        if status in ["COMPLETED", "ERROR"]:
            break
    
    # 8. Check results
    with connection.cursor() as cursor:
        cursor.execute(f"SELECT status FROM extractor_uploadedpdf WHERE id = {pdf.id};")
        final_status = cursor.fetchone()[0]
    
    if final_status == "COMPLETED":
        print("\n✅ Extraction completed successfully!")
        
        # Check for extracted data
        extracted_data = ExtractedData.objects.filter(pdf=pdf)
        print(f"Found {extracted_data.count()} extracted data records:")
        
        for i, data in enumerate(extracted_data, 1):
            print(f"\nExtracted Data #{i}:")
            print(f"  Field: {data.field_name}")
            print(f"  Value: {data.field_value}")
            print(f"  Confidence: {data.confidence}")
    else:
        print(f"\n❌ Extraction failed with status: {pdf.status}")
    
    print("\nTest completed!")

if __name__ == "__main__":
    test_pdf_extraction()
