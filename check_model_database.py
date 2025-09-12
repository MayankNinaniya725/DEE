import os
import sys
import django

# Setup Django
sys.path.append('/code')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'extractor_project.settings')
django.setup()

# Check if the field exists in the database
from django.db import connection

def check_model_vs_database():
    print("Comparing model definition to database schema...")
    
    # Get model fields from Django
    from extractor.models import UploadedPDF
    model_fields = [f.name for f in UploadedPDF._meta.get_fields()]
    print(f"Model fields from Django: {model_fields}")
    
    # Get database columns
    with connection.cursor() as cursor:
        cursor.execute("PRAGMA table_info(extractor_uploadedpdf);")
        db_columns = [col[1] for col in cursor.fetchall()]
        print(f"Database columns: {db_columns}")
    
    # Compare the two
    missing_in_model = [col for col in db_columns if col not in model_fields]
    missing_in_db = [field for field in model_fields if field not in db_columns]
    
    if missing_in_model:
        print(f"Fields in database but not in model: {missing_in_model}")
    if missing_in_db:
        print(f"Fields in model but not in database: {missing_in_db}")
    
    # Create a direct SQL query to get status
    with connection.cursor() as cursor:
        cursor.execute("SELECT id, status FROM extractor_uploadedpdf LIMIT 5;")
        rows = cursor.fetchall()
        print("\nSample data from database:")
        for row in rows:
            print(f"PDF ID: {row[0]}, Status: {row[1]}")

if __name__ == "__main__":
    check_model_vs_database()
