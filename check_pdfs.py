import os
import sys
import django

# Setup Django
sys.path.append('/code')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'extractor_project.settings')
django.setup()

# Import models
from extractor.models import UploadedPDF

def check_pdfs():
    print("Checking PDFs in database...")
    
    # Get total count
    total_pdfs = UploadedPDF.objects.count()
    print(f"Total PDFs in database: {total_pdfs}")
    
    # Show the 5 most recent PDFs
    recent_pdfs = UploadedPDF.objects.all().order_by('-uploaded_at')[:5]
    print("\nMost recent PDFs:")
    for pdf in recent_pdfs:
        print(f"PDF ID: {pdf.id}")
        print(f"  File: {pdf.file.name}")
        print(f"  Vendor: {pdf.vendor.name}")
        print(f"  Uploaded: {pdf.uploaded_at}")
        
        # Check if file exists
        file_path = os.path.join('/code/media', pdf.file.name)
        file_exists = os.path.exists(file_path)
        print(f"  File exists on disk: {file_exists}")
        
        # Check status field
        try:
            status = pdf.status
            print(f"  Status: {status}")
        except Exception as e:
            print(f"  Status field error: {str(e)}")
        
        print()

if __name__ == "__main__":
    check_pdfs()
