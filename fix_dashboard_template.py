import os
import sys
import django

# Setup Django
sys.path.append('/code')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'extractor_project.settings')
django.setup()

def fix_dashboard_template():
    print("Fixing dashboard template to properly display PDFs...")
    
    try:
        # Read the current template
        template_path = '/code/extractor/templates/extractor/dashboard.html'
        with open(template_path, 'r') as f:
            content = f.read()
        
        # Make a backup
        backup_path = '/code/extractor/templates/extractor/dashboard.html.bak'
        with open(backup_path, 'w') as f:
            f.write(content)
        print(f"Created backup at {backup_path}")
        
        # Update the PDF table in the template
        updated_pdf_table = """
            <tbody>
                {% for pdf in recent_pdfs %}
                <tr>
                    <td>{{ pdf.file.name|default:"N/A" }}</td>
                    <td>{{ pdf.vendor.name|default:"N/A" }}</td>
                    <td>
                        {% if pdf.status == 'COMPLETED' %}
                            <span class="badge bg-success">Completed</span>
                        {% elif pdf.status == 'PROCESSING' %}
                            <span class="badge bg-warning text-dark">Processing</span>
                        {% elif pdf.status == 'PENDING' %}
                            <span class="badge bg-secondary">Pending</span>
                        {% elif pdf.status == 'ERROR' %}
                            <span class="badge bg-danger">Error</span>
                        {% else %}
                            <span class="badge bg-light text-dark">{{ pdf.status }}</span>
                        {% endif %}
                    </td>
                    <td>{{ pdf.uploaded_at|date:"Y-m-d H:i:s" }}</td>
                </tr>
                {% empty %}
                <tr><td colspan="4" class="text-center">No PDFs uploaded yet.</td></tr>
                {% endfor %}
            </tbody>"""
        
        # Replace the PDF table in the template
        import re
        pattern = r'<tbody>[\s\S]*?{% empty %}[\s\S]*?{% endfor %}[\s\S]*?</tbody>'
        
        if re.search(pattern, content):
            new_content = re.sub(pattern, updated_pdf_table, content)
            
            # Write the updated content back to the template
            with open(template_path, 'w') as f:
                f.write(new_content)
            
            print("Successfully updated dashboard template.")
        else:
            print("Could not find the PDF table in the template.")
        
    except Exception as e:
        print(f"Error updating dashboard template: {str(e)}")

if __name__ == "__main__":
    fix_dashboard_template()
