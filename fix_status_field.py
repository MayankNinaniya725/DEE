"""
Script to manually add the status field to the UploadedPDF model
"""

import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'extractor_project.settings')
django.setup()

# Import models and migration modules
from django.db import connection
from extractor.models import UploadedPDF

def main():
    # Check if status field exists
    has_status = 'status' in [f.name for f in UploadedPDF._meta.get_fields()]
    
    if has_status:
        print("✅ Status field already exists in the database")
        return True
    
    print("⚠️ Status field missing from database but exists in code")
    
    # Manually add the status field
    with connection.cursor() as cursor:
        try:
            print("Adding status field to extractor_uploadedpdf table...")
            cursor.execute(
                "ALTER TABLE extractor_uploadedpdf ADD COLUMN status varchar(20) NULL"
            )
            print("✅ Status field added successfully")
            
            # Set default value
            print("Setting default value to 'PENDING'...")
            cursor.execute(
                "UPDATE extractor_uploadedpdf SET status = 'PENDING' WHERE status IS NULL"
            )
            print("✅ Default values set")
            return True
        except Exception as e:
            print(f"❌ Error adding status field: {e}")
            return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
