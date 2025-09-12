import os
import sys
import django

# Setup Django
sys.path.append('/code')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'extractor_project.settings')
django.setup()

# Import our models
from django.db import connection
from django.conf import settings

def add_status_field():
    print("Checking if status field exists in UploadedPDF table...")
    
    # Check if the column exists
    with connection.cursor() as cursor:
        # For SQLite, use PRAGMA table_info
        cursor.execute("PRAGMA table_info(extractor_uploadedpdf);")
        columns = [col[1] for col in cursor.fetchall()]
        
        if 'status' in columns:
            print("✅ Status field already exists in the table.")
            return
        
        print("❌ Status field does not exist. Adding it now...")
        
        # Add the status column with default value 'PENDING'
        try:
            cursor.execute("ALTER TABLE extractor_uploadedpdf ADD COLUMN status varchar(20) DEFAULT 'PENDING';")
            print("✅ Successfully added status field to UploadedPDF table.")
        except Exception as e:
            print(f"❌ Error adding status field: {str(e)}")

if __name__ == "__main__":
    add_status_field()
