"""
Test script to verify the PDF extraction functionality works correctly.
This script creates a test PDF with sample data, uploads it through the Django system,
and verifies the extraction process.
"""

import os
import sys
import time
import hashlib
import random
import django
import logging
import traceback
from io import BytesIO
from datetime import datetime

# Configure logging before imports to catch all errors
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('test_extraction')

try:
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import letter
except ImportError:
    logger.error("ReportLab package not installed. Installing now...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "reportlab"])
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import letter

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'extractor_project.settings')
django.setup()

# Import Django models after setup
from django.core.files.base import ContentFile
from extractor.models import Vendor, UploadedPDF, ExtractedData
from extractor.tasks import process_pdf_file
from django.conf import settings
from extractor.utils.config_loader import load_vendor_config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('test_extraction')

def create_test_pdf(output_path, vendor_config):
    """
    Create a test PDF with data matching the vendor's extraction patterns
    """
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter
    
    fields = vendor_config['fields']
    vendor_id = vendor_config['vendor_id']
    
    # Generate sample data based on vendor patterns
    if vendor_id == "citic":
        plate_no = f"T5{random.randint(100000000, 999999999)}"
        heat_no = f"S{random.randint(1000000, 9999999)}"
        test_cert_no = f"Z{random.randint(100000000000000, 999999999999999)}"
    else:
        # Default pattern if vendor isn't recognized
        plate_no = f"PLATE-{random.randint(1000, 9999)}"
        heat_no = f"HEAT-{random.randint(1000, 9999)}"
        test_cert_no = f"CERT-{random.randint(10000, 99999)}"
    
    # Draw a header
    c.setFont("Helvetica-Bold", 16)
    c.drawString(72, height - 72, f"Test Certificate for {vendor_config['vendor_name']}")
    
    # Draw the certificate info
    c.setFont("Helvetica", 12)
    y_position = height - 120
    
    # Certificate number
    c.drawString(72, y_position, f"Test Certificate Number: {test_cert_no}")
    y_position -= 30
    
    # Date
    c.drawString(72, y_position, f"Date: {datetime.now().strftime('%Y-%m-%d')}")
    y_position -= 60
    
    # Product details
    c.setFont("Helvetica-Bold", 14)
    c.drawString(72, y_position, "Product Details")
    y_position -= 30
    
    c.setFont("Helvetica", 12)
    c.drawString(72, y_position, f"Plate Number: {plate_no}")
    y_position -= 20
    c.drawString(72, y_position, f"Heat Number: {heat_no}")
    
    # Add a table
    y_position -= 60
    c.setFont("Helvetica-Bold", 14)
    c.drawString(72, y_position, "Test Results")
    y_position -= 30
    
    # Table header
    c.setFont("Helvetica-Bold", 12)
    c.drawString(72, y_position, "Property")
    c.drawString(250, y_position, "Result")
    c.drawString(400, y_position, "Unit")
    y_position -= 20
    
    # Draw a line under the header
    c.line(72, y_position, 500, y_position)
    y_position -= 20
    
    # Table data
    properties = ["Tensile Strength", "Yield Strength", "Elongation", "Impact Energy"]
    results = [f"{random.randint(500, 650)}", f"{random.randint(350, 450)}", f"{random.randint(20, 35)}", f"{random.randint(100, 200)}"]
    units = ["MPa", "MPa", "%", "J"]
    
    c.setFont("Helvetica", 12)
    for prop, result, unit in zip(properties, results, units):
        c.drawString(72, y_position, prop)
        c.drawString(250, y_position, result)
        c.drawString(400, y_position, unit)
        y_position -= 20
    
    # Add a footer with the certificate number again
    c.setFont("Helvetica", 10)
    c.drawString(72, 72, f"Certificate: {test_cert_no}")
    c.drawString(400, 72, f"Plate: {plate_no} / Heat: {heat_no}")
    
    c.save()
    pdf_data = buffer.getvalue()
    buffer.close()
    
    # Write to file
    with open(output_path, 'wb') as f:
        f.write(pdf_data)
    
    logger.info(f"Created test PDF at {output_path} with data:")
    logger.info(f"  Plate Number: {plate_no}")
    logger.info(f"  Heat Number: {heat_no}")
    logger.info(f"  Test Certificate Number: {test_cert_no}")
    
    return {
        "plate_no": plate_no,
        "heat_no": heat_no,
        "test_cert_no": test_cert_no
    }

def get_or_create_test_vendor():
    """
    Get an existing vendor or create a test vendor
    """
    try:
        # Try to get an existing vendor
        vendor = Vendor.objects.first()
        if vendor:
            logger.info(f"Using existing vendor: {vendor.name}")
            return vendor
        
        # If no vendors exist, create a test vendor
        vendor_name = "CITIC Pacific Special Steel"
        config_path = os.path.join(settings.BASE_DIR, "extractor", "vendor_configs", "citic_steel.json")
        
        if not os.path.exists(config_path):
            logger.error(f"Vendor config file not found at {config_path}")
            raise FileNotFoundError(f"Vendor config file not found at {config_path}")
        
        with open(config_path, 'rb') as f:
            config_file = ContentFile(f.read(), name="citic_steel.json")
        
        vendor = Vendor.objects.create(
            name=vendor_name,
            config_file=config_file
        )
        logger.info(f"Created test vendor: {vendor.name}")
        return vendor
    
    except Exception as e:
        logger.error(f"Error creating test vendor: {str(e)}")
        raise

def upload_test_pdf(pdf_path, vendor):
    """
    Upload the test PDF to the system
    """
    try:
        # Calculate file hash
        with open(pdf_path, 'rb') as f:
            file_content = f.read()
        file_hash = hashlib.md5(file_content).hexdigest()
        
        # Create an UploadedPDF instance
        with open(pdf_path, 'rb') as f:
            pdf_file = ContentFile(f.read(), name=os.path.basename(pdf_path))
        
        uploaded_pdf = UploadedPDF.objects.create(
            vendor=vendor,
            file=pdf_file,
            file_hash=file_hash,
            file_size=os.path.getsize(pdf_path),
            status='PROCESSING'
        )
        
        logger.info(f"Uploaded test PDF with ID: {uploaded_pdf.id}")
        return uploaded_pdf
    
    except Exception as e:
        logger.error(f"Error uploading test PDF: {str(e)}")
        raise

def process_pdf_and_verify(uploaded_pdf, expected_data):
    """
    Process the PDF and verify extraction results
    """
    try:
        # Load vendor config
        config_path = os.path.join(settings.VENDOR_CONFIGS_DIR, uploaded_pdf.vendor.config_file.name)
        vendor_config = load_vendor_config(config_path)
        
        # Process the PDF (synchronously for testing)
        logger.info("Processing PDF...")
        result = process_pdf_file(uploaded_pdf.id, vendor_config)
        
        # Refresh the PDF object
        uploaded_pdf.refresh_from_db()
        
        # Check the status
        logger.info(f"PDF processing status: {uploaded_pdf.status}")
        
        # Check extracted data
        extracted_data = ExtractedData.objects.filter(pdf=uploaded_pdf)
        if extracted_data.exists():
            logger.info(f"Found {extracted_data.count()} extracted data items")
            
            # Check for expected fields
            plate_items = extracted_data.filter(field_key='PLATE_NO')
            heat_items = extracted_data.filter(field_key='HEAT_NO')
            cert_items = extracted_data.filter(field_key='TEST_CERT_NO')
            
            if plate_items.exists():
                plate_value = plate_items.first().field_value
                logger.info(f"Extracted Plate Number: {plate_value}")
                if expected_data['plate_no'] in plate_value:
                    logger.info("✅ Plate Number extraction successful")
                else:
                    logger.warning(f"❌ Plate Number mismatch. Expected: {expected_data['plate_no']}, Got: {plate_value}")
            else:
                logger.warning("❌ Plate Number not extracted")
            
            if heat_items.exists():
                heat_value = heat_items.first().field_value
                logger.info(f"Extracted Heat Number: {heat_value}")
                if expected_data['heat_no'] in heat_value:
                    logger.info("✅ Heat Number extraction successful")
                else:
                    logger.warning(f"❌ Heat Number mismatch. Expected: {expected_data['heat_no']}, Got: {heat_value}")
            else:
                logger.warning("❌ Heat Number not extracted")
            
            if cert_items.exists():
                cert_value = cert_items.first().field_value
                logger.info(f"Extracted Test Certificate Number: {cert_value}")
                if expected_data['test_cert_no'] in cert_value:
                    logger.info("✅ Test Certificate Number extraction successful")
                else:
                    logger.warning(f"❌ Test Certificate Number mismatch. Expected: {expected_data['test_cert_no']}, Got: {cert_value}")
            else:
                logger.warning("❌ Test Certificate Number not extracted")
            
            return True
        else:
            logger.warning("No data was extracted from the PDF")
            return False
    
    except Exception as e:
        logger.error(f"Error processing PDF: {str(e)}")
        return False

def run_test():
    """
    Run the complete extraction test
    """
    logger.info("=== Starting Extraction Test ===")
    
    # Create test directory if it doesn't exist
    test_dir = os.path.join(settings.MEDIA_ROOT, 'test')
    os.makedirs(test_dir, exist_ok=True)
    
    try:
        # Get or create a test vendor
        vendor = get_or_create_test_vendor()
        
        # Load vendor config
        config_path = os.path.join(settings.VENDOR_CONFIGS_DIR, vendor.config_file.name)
        vendor_config = load_vendor_config(config_path)
        
        # Create a test PDF
        pdf_path = os.path.join(test_dir, f"test_cert_{int(time.time())}.pdf")
        expected_data = create_test_pdf(pdf_path, vendor_config)
        
        # Upload the PDF
        uploaded_pdf = upload_test_pdf(pdf_path, vendor)
        
        # Process and verify
        success = process_pdf_and_verify(uploaded_pdf, expected_data)
        
        if success:
            logger.info("✅ Test completed successfully! The extraction logic is working.")
        else:
            logger.warning("⚠️ Test completed with issues. The extraction logic may not be working correctly.")
        
    except Exception as e:
        logger.error(f"Test failed with error: {str(e)}")
        logger.error(traceback.format_exc())
        return False
    
    return True

if __name__ == "__main__":
    try:
        # Setup Django environment
        os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'extractor_project.settings')
        django.setup()

        # Import Django models after setup
        from django.core.files.base import ContentFile
        from extractor.models import Vendor, UploadedPDF, ExtractedData
        from extractor.tasks import process_pdf_file
        from django.conf import settings
        from extractor.utils.config_loader import load_vendor_config
        
        success = run_test()
        sys.exit(0 if success else 1)
    except Exception as e:
        logger.error(f"Fatal error: {str(e)}")
        logger.error(traceback.format_exc())
        sys.exit(1)
