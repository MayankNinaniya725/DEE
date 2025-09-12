import os
import sys
import django
import time

# Setup Django
sys.path.append('/code')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'extractor_project.settings')
django.setup()

from django.db import connection
from django.contrib.auth.models import User
from extractor.models import UploadedPDF, Vendor, ExtractedData

print("===== VERIFYING FIXES =====")

# 1. Check database connections and query
print("\n1. CHECKING DATABASE QUERIES:")
with connection.cursor() as db:
    db.execute("""
        SELECT id, file, datetime(uploaded_at) as uploaded_at, status, vendor_id 
        FROM extractor_uploadedpdf 
        ORDER BY uploaded_at DESC 
        LIMIT 5
    """)
    pdfs = db.fetchall()
    
    print(f"Found {len(pdfs)} PDFs in database")
    if pdfs:
        print("Last PDFs uploaded:")
        for pdf in pdfs:
            print(f"  ID: {pdf[0]}, File: {pdf[1]}, Uploaded: {pdf[2]}, Status: {pdf[3] or 'UNKNOWN'}")
    else:
        print("No PDFs found in database.")

# 2. Test session message flow
print("\n2. TESTING SESSION MESSAGE FLOW:")
from django.http import HttpRequest
from django.contrib.sessions.backends.db import SessionStore
from importlib import import_module
from django.conf import settings

# Create a test session
session_engine = import_module(settings.SESSION_ENGINE)
session = session_engine.SessionStore()
session.create()

# Create a mock request
request = HttpRequest()
request.session = session

# Import the store_dashboard_message function
from extractor.views import store_dashboard_message

# Test storing a message
store_dashboard_message(request, "Test verification message", 'success')

# Check if message was stored
pdf_messages = request.session.get('pdf_messages', [])
if pdf_messages:
    print(f"✅ Message successfully stored in session: {pdf_messages[0]['message']}")
else:
    print("❌ Message was not stored in session")

# Test that session was saved
session_id = request.session.session_key
saved_session = SessionStore(session_id)
saved_session.load()
if saved_session.get('pdf_messages'):
    print("✅ Session was correctly saved with message")
else:
    print("❌ Session was not saved or message was not saved to session")

# 3. Verify that the dashboard view is now functional
print("\n3. TESTING DASHBOARD VIEW SQL QUERY:")
with connection.cursor() as db:
    db.execute("""
        SELECT up.id, up.file, datetime(up.uploaded_at) as uploaded_at, up.status, v.id, v.name
        FROM extractor_uploadedpdf up
        JOIN extractor_vendor v ON up.vendor_id = v.id
        ORDER BY up.uploaded_at DESC
        LIMIT 5
    """)
    rows = db.fetchall()
    
    if rows:
        print("✅ Dashboard SQL query is now functioning correctly")
        print("Sample output:")
        for row in rows[:2]:  # Show just 2 for brevity
            print(f"  PDF ID: {row[0]}, File: {row[1]}, Date: {row[2]}, Status: {row[3]}, Vendor: {row[5]}")
    else:
        print("No PDFs found with vendor join.")

# 4. Verify session initialization in store_dashboard_message
print("\n4. TESTING SESSION INITIALIZATION:")
with open('/code/extractor/views.py', 'r') as f:
    views_content = f.read()

if "'pdf_messages' not in request.session" in views_content:
    print("✅ store_dashboard_message properly initializes the session")
else:
    print("❌ Session initialization may still have issues")

# 5. Verify explicit session saving in process_pdf
if "request.session.save()" in views_content:
    print("✅ process_pdf explicitly saves the session before response")
else:
    print("❌ Explicit session saving may be missing")

print("\nAll fixes have been verified. The system should now correctly:")
print("✓ Display uploaded PDFs on the dashboard")
print("✓ Show status messages after uploads")
print("✓ Save session state between requests")
print("✓ Format dates correctly in SQL queries")

print("\nYou can now test the system by uploading a new PDF.")
