import os
import sys
import django

# Setup Django
sys.path.append('/code')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'extractor_project.settings')
django.setup()

# Import required modules
from django.db import connection

def check_extracted_data_schema():
    print("Checking ExtractedData table schema...")
    
    with connection.cursor() as cursor:
        cursor.execute("PRAGMA table_info(extractor_extracteddata);")
        columns = cursor.fetchall()
        
        print("Columns in extractor_extracteddata:")
        for col in columns:
            print(f"  {col[1]} ({col[2]})")

if __name__ == "__main__":
    check_extracted_data_schema()
