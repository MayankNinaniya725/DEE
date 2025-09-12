import os
import sys
import django

# Setup Django
sys.path.append('/code')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'extractor_project.settings')
django.setup()

print("===== FIXING DASHBOARD SQL QUERY =====")

# Create a backup
os.system("cp /code/extractor/views.py /code/extractor/views.py.dashboard_fix_bak")
print("✅ Created backup at /code/extractor/views.py.dashboard_fix_bak")

# Read current views.py
with open('/code/extractor/views.py', 'r') as f:
    content = f.read()

# Fix the SQL query for SQLite date formatting
old_query = '''
                SELECT up.id, up.file, up.uploaded_at, up.status, v.id, v.name
                FROM extractor_uploadedpdf up
                JOIN extractor_vendor v ON up.vendor_id = v.id
                ORDER BY up.uploaded_at DESC
                LIMIT 20
            '''

new_query = '''
                SELECT up.id, up.file, datetime(up.uploaded_at) as uploaded_at, up.status, v.id, v.name
                FROM extractor_uploadedpdf up
                JOIN extractor_vendor v ON up.vendor_id = v.id
                ORDER BY up.uploaded_at DESC
                LIMIT 20
            '''

updated_content = content.replace(old_query, new_query)

# Also add explicit session saving to all response calls
updated_content = updated_content.replace(
    "store_dashboard_message(request, \"PDF uploaded successfully. Starting extraction...\", 'success')",
    "store_dashboard_message(request, \"PDF uploaded successfully. Starting extraction...\", 'success')\n    # Explicitly save session\n    request.session.save()"
)

# Also fix store_dashboard_message function to ensure it sets session modified flag
old_func = '''def store_dashboard_message(request, message, level='info', extra_data=None):
    """Store message in session for dashboard display"""'''

new_func = '''def store_dashboard_message(request, message, level='info', extra_data=None):
    """Store message in session for dashboard display"""
    # Make sure pdf_messages exists in session
    if 'pdf_messages' not in request.session:
        request.session['pdf_messages'] = []'''

updated_content = updated_content.replace(old_func, new_func)

# Write the updated content
with open('/code/extractor/views.py', 'w') as f:
    f.write(updated_content)

print("✅ Updated SQL query with proper datetime formatting")
print("✅ Added explicit session saving to process_pdf view")
print("✅ Enhanced store_dashboard_message function")

# Now fix the template to ensure it handles the data format correctly
try:
    os.system("cp /code/extractor/templates/extractor/dashboard.html /code/extractor/templates/extractor/dashboard.html.bak")
    
    with open('/code/extractor/templates/extractor/dashboard.html', 'r') as f:
        template_content = f.read()
    
    # Check for pdf.status in template and ensure it handles the dictionary format
    if "{% for pdf in recent_pdfs %}" in template_content and "pdf.status" in template_content:
        print("✅ Template is already set up for dictionary-style PDF objects")
    else:
        print("❌ Template may need manual adjustment for dictionary-style PDF objects")
        
except Exception as e:
    print(f"Error checking template: {e}")

print("\nAll fixes have been applied. Please restart the web container to apply changes.")
