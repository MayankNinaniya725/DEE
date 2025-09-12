import os
import sys
import django

# Setup Django
sys.path.append('/code')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'extractor_project.settings')
django.setup()

from django.db import connection
from extractor.models import Vendor, ExtractedData
from django.db.models import Count

# Check if our dashboard view correctly handles SQLite date formats
print("===== CHECKING DASHBOARD VIEW SQL QUERY =====")

# First, get the dashboard view implementation
with connection.cursor() as db:
    try:
        # Execute the query that should be in the dashboard view
        db.execute("""
            SELECT id, file, file_hash, file_size, uploaded_at, vendor_id, status 
            FROM extractor_uploadedpdf 
            ORDER BY uploaded_at DESC 
            LIMIT 5
        """)
        recent_pdfs = db.fetchall()
        
        print("\nCurrent query result format:")
        for pdf in recent_pdfs[:2]:  # Show just 2 records for brevity
            print(f"  ID: {pdf[0]}, File: {pdf[1]}, Uploaded at: {pdf[4]}, Status: {pdf[6] or 'UNKNOWN'}")
            
        # Now try with the SQLite date function
        db.execute("""
            SELECT id, file, file_hash, file_size, 
                   datetime(uploaded_at) as uploaded_at, 
                   vendor_id, status 
            FROM extractor_uploadedpdf 
            ORDER BY uploaded_at DESC 
            LIMIT 5
        """)
        fixed_pdfs = db.fetchall()
        
        print("\nImproved query result format:")
        for pdf in fixed_pdfs[:2]:  # Show just 2 records for brevity
            print(f"  ID: {pdf[0]}, File: {pdf[1]}, Uploaded at: {pdf[4]}, Status: {pdf[6] or 'UNKNOWN'}")
            
        # Check if we need to update the views.py file
        if recent_pdfs == fixed_pdfs:
            print("\nNo query fix needed - date formatting is already correct.")
        else:
            print("\nSQL query needs to be updated for proper date formatting.")
            
            # Create backup of views.py
            os.system("cp /code/extractor/views.py /code/extractor/views.py.query_fix_bak")
            
            # Read the current content
            with open("/code/extractor/views.py", "r") as f:
                content = f.read()
                
            # Look for the dashboard query and replace it
            old_query = """
            SELECT id, file, file_hash, file_size, uploaded_at, vendor_id, status 
            FROM extractor_uploadedpdf 
            ORDER BY uploaded_at DESC 
            LIMIT 20
        """
            
            new_query = """
            SELECT id, file, file_hash, file_size, 
                   datetime(uploaded_at) as uploaded_at, 
                   vendor_id, status 
            FROM extractor_uploadedpdf 
            ORDER BY uploaded_at DESC 
            LIMIT 20
        """
            
            if old_query in content:
                updated_content = content.replace(old_query, new_query)
                
                # Update views.py
                with open("/code/extractor/views.py", "w") as f:
                    f.write(updated_content)
                    
                print("✅ Dashboard query fixed in views.py")
                print("✅ Backup created at /code/extractor/views.py.query_fix_bak")
            else:
                print("❌ Could not locate the dashboard SQL query in views.py")
                print("   Manual intervention required.")
                
        # Now let's check session saving in store_dashboard_message function
        print("\nChecking store_dashboard_message function...")
        
        with open("/code/extractor/views.py", "r") as f:
            views_content = f.read()
            
        # Look for session.save() in process_pdf view
        if "request.session.save()" in views_content:
            print("✅ Session is already being explicitly saved")
        else:
            print("❌ No explicit session.save() call found")
            print("   Adding session.save() call to process_pdf view...")
            
            # Create another backup
            os.system("cp /code/extractor/views.py /code/extractor/views.py.session_fix_bak")
            
            # Add session.save() before JsonResponse in process_pdf view
            updated_content = views_content.replace(
                "store_dashboard_message(request, \"PDF uploaded successfully. Starting extraction...\", 'success')",
                "store_dashboard_message(request, \"PDF uploaded successfully. Starting extraction...\", 'success')\n    # Explicitly save session\n    request.session.save()"
            )
            
            if updated_content != views_content:
                with open("/code/extractor/views.py", "w") as f:
                    f.write(updated_content)
                print("✅ Added explicit session.save() call to process_pdf view")
            else:
                print("❌ Could not add session.save() call - pattern not found")
                
    except Exception as e:
        print(f"Error executing SQL query: {e}")
        print("This might be a syntax issue specific to your database backend.")
        
print("\nFix complete. Please restart the web container to apply changes.")
