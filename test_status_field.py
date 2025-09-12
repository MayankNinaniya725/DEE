import os
import sys
import django

# Setup Django
sys.path.append('/code')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'extractor_project.settings')
django.setup()

# Import our models
from extractor.models import UploadedPDF

def test_status_field():
    print("Testing status field in UploadedPDF model...")
    
    # Get all PDFs
    pdfs = UploadedPDF.objects.all()
    print(f"Found {pdfs.count()} PDFs in the database")
    
    if not pdfs.exists():
        print("No PDFs found. Nothing to test.")
        return
    
    # Get the first PDF
    pdf = pdfs.first()
    print(f"Testing with PDF: {pdf.file.name} (ID: {pdf.id})")
    
    # Try to get current status
    print(f"Current status: {pdf.status}")
    
    # Try to update status
    try:
        pdf.status = 'PROCESSING'
        pdf.save()
        print("✅ Successfully updated status field to 'PROCESSING'")
    except Exception as e:
        print(f"❌ Error updating status field: {str(e)}")
    
    # Create a new PDF with status field
    try:
        # Get values from existing PDF to create similar test PDF
        new_pdf = UploadedPDF(
            file=pdf.file,
            vendor=pdf.vendor,
            file_hash=pdf.file_hash + "_test",
            file_size=pdf.file_size,
            status='PENDING'
        )
        new_pdf.save()
        print(f"✅ Successfully created new PDF with status 'PENDING' (ID: {new_pdf.id})")
    except Exception as e:
        print(f"❌ Error creating new PDF with status field: {str(e)}")

if __name__ == "__main__":
    test_status_field()
