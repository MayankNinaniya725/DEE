import os
import sys
import django
import time

# Setup Django
sys.path.append('/code')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'extractor_project.settings')
django.setup()

# Import required modules
from django.conf import settings
from extractor.models import Vendor
from extractor.utils.config_loader import load_vendor_config
from extractor.tasks import process_pdf_file
import hashlib
from django.db import connection

def test_minimal_extraction():
    print("Starting minimal extraction test...")
    
    # 1. Get a vendor
    vendors = Vendor.objects.all()
    if not vendors.exists():
        print("No vendors found. Exiting.")
        return
    vendor = vendors.first()
    print(f"Using vendor: {vendor.name}")
    
    # 2. Load vendor config
    config_path = os.path.join(settings.MEDIA_ROOT, vendor.config_file.name)
    vendor_config = load_vendor_config(config_path)
    print("Loaded vendor config")
    
    # 3. Find existing PDF in database
    with connection.cursor() as cursor:
        cursor.execute("SELECT id FROM extractor_uploadedpdf LIMIT 1")
        result = cursor.fetchone()
        if not result:
            print("No PDFs found in database. Exiting.")
            return
        pdf_id = result[0]
    
    print(f"Using existing PDF with ID: {pdf_id}")
    
    # 4. Call the task directly
    print("Starting extraction task...")
    try:
        task = process_pdf_file.delay(pdf_id, vendor_config)
        print(f"Task started with ID: {task.id}")
    except Exception as e:
        print(f"Error starting task: {str(e)}")
        return
    
    # 5. Wait for task completion
    print("\nWaiting for task completion...")
    for i in range(30):  # Wait up to 30 seconds
        time.sleep(1)
        
        # Check status directly in database
        with connection.cursor() as cursor:
            cursor.execute(f"SELECT status FROM extractor_uploadedpdf WHERE id = {pdf_id}")
            status = cursor.fetchone()[0]
        
        status_emoji = "✅" if status == "COMPLETED" else "⏳" if status == "PROCESSING" else "❌"
        print(f"Status: {status_emoji} {status} (waited {i+1}s)")
        
        if status in ["COMPLETED", "ERROR"]:
            break
    
    # 6. Check for extracted data
    with connection.cursor() as cursor:
        cursor.execute(f"SELECT COUNT(*) FROM extractor_extracteddata WHERE pdf_id = {pdf_id}")
        count = cursor.fetchone()[0]
    
    print(f"\nFound {count} extracted data records")
    
    if count > 0:
        # Print some sample data
        with connection.cursor() as cursor:
            cursor.execute(f"SELECT field_key, field_value, page_number FROM extractor_extracteddata WHERE pdf_id = {pdf_id} LIMIT 5")
            rows = cursor.fetchall()
        
        print("\nSample extracted data:")
        for row in rows:
            print(f"Field Key: {row[0]}")
            print(f"Value: {row[1]}")
            print(f"Page Number: {row[2]}")
            print("---")
    
    print("Test completed!")

if __name__ == "__main__":
    test_minimal_extraction()
