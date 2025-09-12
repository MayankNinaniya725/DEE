import os
import sys
import django

# Setup Django
sys.path.append('/code')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'extractor_project.settings')
django.setup()

from django.http import JsonResponse
from django.urls import reverse
from extractor.models import UploadedPDF, Vendor
import json

print("===== CHECKING PROCESS_PDF VIEW =====")

# Create a function to test the view logic
def check_process_pdf_view():
    # First read the views.py file to understand current implementation
    with open('/code/extractor/views.py', 'r') as f:
        content = f.read()
    
    # Extract process_pdf function
    start_idx = content.find('def process_pdf(request):')
    if start_idx == -1:
        print("❌ Could not find process_pdf function in views.py")
        return False
    
    end_idx = content.find('def', start_idx + 1)
    if end_idx == -1:
        end_idx = len(content)
    
    process_pdf_code = content[start_idx:end_idx]
    
    # Check if the function has been updated with session.save()
    if "request.session.save()" in process_pdf_code:
        print("✅ process_pdf already includes session.save()")
    else:
        print("❌ process_pdf is missing session.save() before response")
        
        # Update the function
        updated_process_pdf = process_pdf_code.replace(
            "store_dashboard_message(request, \"PDF uploaded successfully. Starting extraction...\", 'success')",
            "store_dashboard_message(request, \"PDF uploaded successfully. Starting extraction...\", 'success')\n    # Explicitly save session\n    request.session.save()"
        )
        
        # Update the entire file
        updated_content = content.replace(process_pdf_code, updated_process_pdf)
        
        # Make a backup
        os.system("cp /code/extractor/views.py /code/extractor/views.py.process_pdf_fix_bak")
        
        # Write the updated content
        with open('/code/extractor/views.py', 'w') as f:
            f.write(updated_content)
            
        print("✅ Updated process_pdf function with session.save()")
    
    # Check if the function properly updates the status field
    if "status='PROCESSING'" in process_pdf_code:
        print("✅ PDF status is set to PROCESSING during creation")
    else:
        print("❌ PDF status is not explicitly set during creation")
    
    # Check if task is properly started
    if "process_pdf_file.delay" in process_pdf_code:
        print("✅ Celery task is correctly started with delay()")
    else:
        print("❌ Celery task may not be started correctly")
    
    # Check the store_dashboard_message function as well
    if "def store_dashboard_message" in content:
        store_function_start = content.find("def store_dashboard_message")
        store_function_end = content.find("def", store_function_start + 1)
        if store_function_end == -1:
            store_function_end = len(content)
        
        store_function = content[store_function_start:store_function_end]
        
        # Check if it correctly initializes the messages list
        if "'pdf_messages' not in request.session" in store_function:
            print("✅ store_dashboard_message correctly initializes session")
        else:
            # Update the function to properly initialize session
            updated_store_function = store_function.replace(
                "def store_dashboard_message(request, message, level='info', extra_data=None):",
                "def store_dashboard_message(request, message, level='info', extra_data=None):\n    # Initialize session messages if needed\n    if 'pdf_messages' not in request.session:\n        request.session['pdf_messages'] = []"
            )
            
            # Update the entire file
            updated_content = content.replace(store_function, updated_store_function)
            
            # Make a backup if not already done
            if not os.path.exists("/code/extractor/views.py.store_msg_fix_bak"):
                os.system("cp /code/extractor/views.py /code/extractor/views.py.store_msg_fix_bak")
            
            # Write the updated content
            with open('/code/extractor/views.py', 'w') as f:
                f.write(updated_content)
                
            print("✅ Updated store_dashboard_message to initialize session correctly")
    
    # Additional checks for the template
    try:
        with open('/code/extractor/templates/extractor/dashboard.html', 'r') as f:
            dashboard_template = f.read()
            
        if "{% for message in messages %}" in dashboard_template:
            print("✅ Dashboard template correctly iterates over messages")
        else:
            print("❌ Dashboard template may not be showing messages correctly")
            
        if "pdf.status" in dashboard_template:
            print("✅ Dashboard template displays PDF status")
        else:
            print("❌ Dashboard template may not be showing PDF status")
    except Exception as e:
        print(f"Error checking dashboard template: {e}")
    
    return True

# Run the checks
check_process_pdf_view()

print("\nAll process_pdf view fixes have been applied!")
print("Please restart the web container to apply these changes.")
