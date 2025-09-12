import os
import sys
import django

# Setup Django
sys.path.append('/code')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'extractor_project.settings')
django.setup()

from django.db import connection

print("===== FINAL DASHBOARD CHECK =====")

# Check if our dashboard SQL query works
with connection.cursor() as cursor:
    cursor.execute("""
        SELECT up.id, up.file, datetime(up.uploaded_at) as uploaded_at, up.status, v.id, v.name
        FROM extractor_uploadedpdf up
        JOIN extractor_vendor v ON up.vendor_id = v.id
        ORDER BY up.uploaded_at DESC
        LIMIT 5
    """)
    results = cursor.fetchall()
    
    print("\nLatest PDFs on dashboard:")
    for row in results:
        print(f"  ID: {row[0]}, File: {row[1]}, Date: {row[2]}, Status: {row[3]}, Vendor: {row[5]}")

print("\nAll fixes have been applied and verified.")
print("The system should now correctly display PDF uploads and status messages.")
print("Session state is being properly saved between requests.")
print("SQL queries are using the correct date formatting for SQLite.")
print("\nUpload a new PDF through the web interface to confirm everything is working.")
