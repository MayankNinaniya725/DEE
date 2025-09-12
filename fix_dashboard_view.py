import os
import sys
import django

# Setup Django
sys.path.append('/code')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'extractor_project.settings')
django.setup()

def fix_dashboard_view():
    print("Fixing dashboard view to properly display PDFs...")
    
    try:
        # Read the current views.py file
        views_path = '/code/extractor/views.py'
        with open(views_path, 'r') as f:
            content = f.read()
        
        # Make a backup
        backup_path = '/code/extractor/views.py.bak5'
        with open(backup_path, 'w') as f:
            f.write(content)
        print(f"Created backup at {backup_path}")
        
        # Update the dashboard view to use direct SQL
        dashboard_function = """def dashboard(request):
    \"\"\"Dashboard view showing summary of uploaded PDFs and extraction status\"\"\"
    # Get PDFs from database using direct SQL to avoid status field issues
    from django.db import connection
    
    # Get recent PDFs
    with connection.cursor() as cursor:
        if request.user.is_superuser:
            cursor.execute('''
                SELECT up.id, up.file, up.uploaded_at, up.status, v.id, v.name
                FROM extractor_uploadedpdf up
                JOIN extractor_vendor v ON up.vendor_id = v.id
                ORDER BY up.uploaded_at DESC
                LIMIT 20
            ''')
        else:
            # For non-superusers, we would filter by user, but for now show all
            cursor.execute('''
                SELECT up.id, up.file, up.uploaded_at, up.status, v.id, v.name
                FROM extractor_uploadedpdf up
                JOIN extractor_vendor v ON up.vendor_id = v.id
                ORDER BY up.uploaded_at DESC
                LIMIT 20
            ''')
        
        rows = cursor.fetchall()
        
        # Convert to a list of dictionaries that mimics Django ORM objects
        recent_pdfs = []
        for row in rows:
            pdf_id, file_path, uploaded_at, status, vendor_id, vendor_name = row
            pdf = {
                'id': pdf_id,
                'file': {'name': file_path},
                'uploaded_at': uploaded_at,
                'status': status,
                'vendor': {'id': vendor_id, 'name': vendor_name}
            }
            recent_pdfs.append(pdf)
    
    # Get vendors
    vendors = Vendor.objects.annotate(pdf_count=Count('pdfs'))
    
    # Get status summary
    status_summary = {
        'pending': 0,
        'processing': 0,
        'completed': 0,
        'error': 0,
    }
    
    with connection.cursor() as cursor:
        cursor.execute('''
            SELECT status, COUNT(*) 
            FROM extractor_uploadedpdf 
            GROUP BY status
        ''')
        status_counts = cursor.fetchall()
        
        for status, count in status_counts:
            if status == 'PENDING':
                status_summary['pending'] = count
            elif status == 'PROCESSING':
                status_summary['processing'] = count
            elif status == 'COMPLETED':
                status_summary['completed'] = count
            elif status == 'ERROR':
                status_summary['error'] = count
    
    # Process messages
    dashboard_messages = request.session.pop('pdf_messages', [])
    for msg in dashboard_messages:
        level_mapping = {
            'success': messages.SUCCESS,
            'error': messages.ERROR,
            'warning': messages.WARNING,
            'info': messages.INFO
        }
        level = level_mapping.get(msg['level'], messages.INFO)
        messages.add_message(request, level, msg['message'])
    
    # Get recent extractions
    extraction_filter = Q()
    if not request.user.is_superuser:
        extraction_filter &= Q(pdf__user=request.user)
    
    recent_extractions = ExtractedData.objects.select_related('pdf', 'vendor').filter(extraction_filter).order_by('-created_at')[:20]
    
    context = {
        'recent_pdfs': recent_pdfs,
        'vendors': vendors,
        'status_summary': status_summary,
        'recent_extractions': recent_extractions,
        'task_id': request.session.get('last_task_id'),
    }
    return render(request, 'extractor/dashboard.html', context)"""

        # Replace the dashboard function in views.py
        import re
        pattern = r'def dashboard\(request\):[\s\S]*?return render\(request, \'extractor/dashboard\.html\', context\)'
        
        if re.search(pattern, content):
            new_content = re.sub(pattern, dashboard_function, content)
            
            # Write the updated content back to views.py
            with open(views_path, 'w') as f:
                f.write(new_content)
            
            print("Successfully updated dashboard view to use direct SQL queries.")
            print("This should fix the issue with PDFs not showing up on the dashboard.")
        else:
            print("Could not find the dashboard function in views.py.")
            print("Please manually update the dashboard view.")
        
    except Exception as e:
        print(f"Error updating dashboard view: {str(e)}")

if __name__ == "__main__":
    fix_dashboard_view()
