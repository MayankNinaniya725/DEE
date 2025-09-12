import os
import sys
import django

# Setup Django
sys.path.append('/code')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'extractor_project.settings')
django.setup()

# Check database schema for the UploadedPDF table
from django.db import connection

def check_database_schema():
    print("Checking database schema for UploadedPDF table...")
    
    with connection.cursor() as cursor:
        cursor.execute("PRAGMA table_info(extractor_uploadedpdf);")
        columns = cursor.fetchall()
        
        print("Columns in extractor_uploadedpdf:")
        for col in columns:
            print(f"  {col[1]} ({col[2]})")

    # Count PDFs by status if it exists
    status_column_exists = any(col[1] == 'status' for col in columns)
    if status_column_exists:
        print("\nPDF count by status:")
        with connection.cursor() as cursor:
            cursor.execute("SELECT status, COUNT(*) FROM extractor_uploadedpdf GROUP BY status;")
            status_counts = cursor.fetchall()
            for status, count in status_counts:
                print(f"  {status}: {count}")
    else:
        print("\nThe 'status' column does not exist in the extractor_uploadedpdf table.")
        print("This means status updates won't work, and the dashboard can't show PDF status.")

if __name__ == "__main__":
    check_database_schema()
