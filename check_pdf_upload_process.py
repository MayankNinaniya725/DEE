import os
import sys
import django
from datetime import datetime, timedelta

# Setup Django
sys.path.append('/code')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'extractor_project.settings')
django.setup()

# Import database models
from django.db import connection
from django.utils import timezone

def check_pdf_upload_process():
    print("===== CHECKING PDF UPLOAD PROCESS =====")
    
    # 1. Check recent PDF uploads in database (last 24 hours)
    print("\n1. RECENT PDF UPLOADS IN DATABASE:")
    with connection.cursor() as cursor:
        # For SQLite, we need to use a different timestamp format
        time_threshold = (timezone.now() - timedelta(hours=24)).strftime('%Y-%m-%d %H:%M:%S')
        cursor.execute("""
            SELECT id, file, file_hash, uploaded_at, status, vendor_id 
            FROM extractor_uploadedpdf
            WHERE uploaded_at > datetime(?)
            ORDER BY uploaded_at DESC
            LIMIT 10
        """, [time_threshold])
        
        recent_pdfs = cursor.fetchall()
        
        if recent_pdfs:
            print(f"Found {len(recent_pdfs)} PDFs uploaded in the last 24 hours:")
            for pdf in recent_pdfs:
                pdf_id, file_path, file_hash, uploaded_at, status, vendor_id = pdf
                print(f"  ID: {pdf_id}")
                print(f"  File: {file_path}")
                print(f"  Status: {status}")
                print(f"  Uploaded: {uploaded_at}")
                print(f"  Vendor ID: {vendor_id}")
                
                # Check if file exists on disk
                full_path = os.path.join('/code/media', file_path)
                print(f"  File exists on disk: {os.path.exists(full_path)}")
                print("")
        else:
            print("No PDFs uploaded in the last 24 hours.")
    
    # 2. Check session messages in the database
    print("\n2. CHECKING SESSION DATA FOR MESSAGES:")
    with connection.cursor() as cursor:
        cursor.execute("SELECT session_key, expire_date, session_data FROM django_session ORDER BY expire_date DESC LIMIT 5")
        sessions = cursor.fetchall()
        
        if sessions:
            print(f"Found {len(sessions)} active sessions:")
            for session in sessions:
                key, expire, data = session
                print(f"  Session: {key} (expires: {expire})")
                print(f"  Data length: {len(data) if data else 0} bytes")
                # We can't easily decode the session data here, but we can check if it exists
        else:
            print("No active sessions found.")
    
    # 3. Check logs for upload-related entries
    print("\n3. CHECKING LOGS FOR UPLOAD ACTIVITY:")
    log_files = [
        '/code/logs/extractor.log',
        '/code/extractor/logs/errors.log'
    ]
    
    for log_file in log_files:
        if os.path.exists(log_file):
            print(f"\nExamining log file: {log_file}")
            try:
                # Get the last 20 lines from the log file
                with open(log_file, 'r') as f:
                    lines = f.readlines()
                    last_lines = lines[-20:]
                
                upload_related_lines = []
                for line in last_lines:
                    if any(keyword in line.lower() for keyword in ['upload', 'pdf', 'process_pdf', 'notification', 'dashboard']):
                        upload_related_lines.append(line.strip())
                
                if upload_related_lines:
                    print(f"Found {len(upload_related_lines)} upload-related log entries:")
                    for line in upload_related_lines:
                        print(f"  {line}")
                else:
                    print("No upload-related log entries found in the last 20 lines.")
            except Exception as e:
                print(f"Error reading log file: {str(e)}")
        else:
            print(f"Log file not found: {log_file}")
    
    # 4. Check Celery tasks related to PDF processing
    print("\n4. CHECKING CELERY TASKS FOR PDF PROCESSING:")
    # We would need Redis to check the Celery tasks, but we can check the status in the database
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT status, COUNT(*) 
            FROM extractor_uploadedpdf 
            GROUP BY status
        """)
        status_counts = cursor.fetchall()
        
        print("PDF status counts:")
        for status, count in status_counts:
            print(f"  {status}: {count}")
    
    # 5. Check if the dashboard view is working correctly
    print("\n5. CHECKING DASHBOARD VIEW:")
    try:
        import inspect
        from extractor.views import dashboard
        
        # Get the source code of the dashboard function
        dashboard_source = inspect.getsource(dashboard)
        
        print("Dashboard view source:")
        print("---")
        print(dashboard_source[:200] + "..." if len(dashboard_source) > 200 else dashboard_source)
        print("---")
        
        # Check if the view is using direct SQL or Django ORM
        if "connection.cursor()" in dashboard_source:
            print("Dashboard view is using direct SQL queries.")
        else:
            print("Dashboard view is using Django ORM.")
            
        # Check if the view is looking for the status field
        if "status" in dashboard_source:
            print("Dashboard view is checking the status field.")
        else:
            print("Dashboard view doesn't seem to be checking the status field.")
    except Exception as e:
        print(f"Error checking dashboard view: {str(e)}")

if __name__ == "__main__":
    check_pdf_upload_process()
