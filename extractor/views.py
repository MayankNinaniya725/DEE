# extractor/views.py
import os
import json
import logging
from django.shortcuts import render, redirect
from django.core.files.storage import FileSystemStorage
from django.contrib import messages
from django.db.models import Count
from django.core.exceptions import ValidationError
from django.conf import settings
from .models import ExtractedData, Vendor, UploadedPDF
from .utils.extractor import extract_pdf_fields
from .utils.config_loader import load_vendor_config
from .tasks import process_pdf_file

# Setup logging
import logging.handlers

# Create logs directory if it doesn't exist
log_dir = os.path.join(settings.BASE_DIR, 'logs')
os.makedirs(log_dir, exist_ok=True)

# Configure logging
logger = logging.getLogger('extractor')
logger.setLevel(logging.DEBUG)

# File handler for all logs
file_handler = logging.handlers.RotatingFileHandler(
    os.path.join(log_dir, 'extractor.log'),
    maxBytes=1024*1024,  # 1MB
    backupCount=5
)
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
))
logger.addHandler(file_handler)

# Error file handler
error_handler = logging.handlers.RotatingFileHandler(
    os.path.join(log_dir, 'errors.log'),
    maxBytes=1024*1024,  # 1MB
    backupCount=5
)
error_handler.setLevel(logging.ERROR)
error_handler.setFormatter(logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
))
logger.addHandler(error_handler)

print("extractor.views module loaded - Logging configured")

def dashboard(request):
    # Get latest data first, with related vendor and PDF info
    data = ExtractedData.objects.select_related('vendor', 'pdf').order_by('-created_at')
    
    # Get counts for summary
    total_pdfs = UploadedPDF.objects.count()
    total_extracted = ExtractedData.objects.values('pdf').distinct().count()
    
    from django.utils import timezone
    
    context = {
        "data": data,
        "total_pdfs": total_pdfs,
        "total_extracted": total_extracted,
        "messages": messages.get_messages(request),  # Get any messages from upload
        "now": timezone.now()  # Add current time for last update display
    }
    return render(request, "extractor/dashboard.html", context)

def upload_pdf(request):
    vendors = Vendor.objects.annotate(pdf_count=Count('pdfs')).order_by('name')
    
    if request.method == "POST":
        try:
            logger.info("Processing PDF upload request")
            vendor_id = request.POST.get("vendor")
            uploaded_file = request.FILES.get("pdf")
            
            logger.debug(f"Received vendor_id: {vendor_id}")
            logger.debug(f"Received file: {uploaded_file.name if uploaded_file else None}")
            
            # Validation
            if not vendor_id:
                raise ValidationError("Please select a vendor")
            if not uploaded_file:
                raise ValidationError("Please select a PDF file")
            if not uploaded_file.name.lower().endswith('.pdf'):
                raise ValidationError("Only PDF files are allowed")
            
            # Get vendor
            try:
                vendor = Vendor.objects.get(id=vendor_id)
            except Vendor.DoesNotExist:
                raise ValidationError("Invalid vendor selected")
            
            # Save uploaded PDF
            try:
                uploaded_pdf = UploadedPDF.objects.create(
                    vendor=vendor,
                    file=uploaded_file
                )
            except Exception as e:
                raise ValidationError(f"Error saving PDF: {str(e)}")
            
            # Create necessary directories
            media_root = settings.MEDIA_ROOT
            upload_dir = os.path.join(media_root, 'uploads')
            extracted_dir = os.path.join(media_root, 'extracted')
            os.makedirs(upload_dir, exist_ok=True)
            os.makedirs(extracted_dir, exist_ok=True)

            # Load vendor config
            try:
                # Extract vendor short name (e.g., "JSW Steel" -> "jsw")
                vendor_name = vendor.name.split()[0].lower()
                logger.info(f"Loading config for vendor: {vendor_name}")
                
                # Check both possible locations for vendor config
                vendor_config_path = os.path.join(settings.BASE_DIR, 'extractor', 'vendor_configs', f"{vendor_name}_steel.json")
                media_config_path = os.path.join(settings.MEDIA_ROOT, 'vendor_configs', f"{vendor_name}_steel.json")
                
                if os.path.exists(vendor_config_path):
                    config_path = vendor_config_path
                elif os.path.exists(media_config_path):
                    config_path = media_config_path
                else:
                    available_configs = []
                    for path in [os.path.join(settings.BASE_DIR, 'extractor', 'vendor_configs'), 
                               os.path.join(settings.MEDIA_ROOT, 'vendor_configs')]:
                        if os.path.exists(path):
                            available_configs.extend(os.listdir(path))
                    
                    logger.error(f"Vendor config not found. Available configs: {available_configs}")
                    raise ValidationError(f"Vendor configuration file not found for {vendor.name}")
                
                logger.info(f"Using config file: {config_path}")
                
                with open(config_path, 'r') as f:
                    vendor_config = json.load(f)
                
                # Validate config structure
                required_fields = ['vendor_id', 'vendor_name', 'fields']
                missing_fields = [field for field in required_fields if field not in vendor_config]
                if missing_fields:
                    raise ValidationError(f"Invalid vendor config: missing {', '.join(missing_fields)}")
                
                required_field_patterns = ['PLATE_NO', 'HEAT_NO', 'TEST_CERT_NO']
                missing_patterns = [field for field in required_field_patterns if field not in vendor_config['fields']]
                if missing_patterns:
                    raise ValidationError(f"Invalid vendor config: missing patterns for {', '.join(missing_patterns)}")
                
                logger.info(f"Successfully loaded vendor config: {vendor_config}")
            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON in vendor config: {str(e)}")
                raise ValidationError(f"Invalid vendor configuration file format: {str(e)}")
            except Exception as e:
                logger.error(f"Error loading vendor config: {str(e)}")
                raise ValidationError(f"Error loading vendor configuration: {str(e)}")
            
            # Run extraction
            try:
                # Enhanced logging for troubleshooting
                logger.info("=== Starting Extraction Process ===")
                logger.info(f"PDF Path: {uploaded_pdf.file.path}")
                logger.info(f"Vendor: {vendor.name}")
                logger.info(f"Vendor Config: {vendor_config}")
                
                # Verify file accessibility
                if not os.path.exists(uploaded_pdf.file.path):
                    raise ValidationError(f"PDF file not found at {uploaded_pdf.file.path}")
                
                file_size = os.path.getsize(uploaded_pdf.file.path)
                logger.info(f"File size: {file_size} bytes")
                
                if file_size == 0:
                    raise ValidationError("PDF file is empty")
                
                # Verify output directory
                output_dir = os.path.join(settings.MEDIA_ROOT, 'extracted')
                os.makedirs(output_dir, exist_ok=True)
                logger.info(f"Output directory ready: {output_dir}")
                
                # Queue the extraction task
                logger.info("Queueing extraction task...")
                task = process_pdf_file.delay(uploaded_pdf.id, vendor_config)
                logger.info(f"Extraction task queued with ID: {task.id}")
                
                messages.success(request, "PDF uploaded successfully. Processing started in background.")
                return redirect("dashboard")
                    
            except Exception as e:
                logger.error("=== Extraction Failed ===")
                logger.error(f"Error type: {type(e).__name__}")
                logger.error(f"Error message: {str(e)}")
                logger.error("Full traceback:", exc_info=True)
                raise ValidationError(f"Error during extraction: {str(e)}")
            
            if not extracted_data:
                logger.warning("No data extracted from PDF")
                raise ValidationError("No data could be extracted from the PDF")
            
            # Save extracted data
            extraction_count = 0
            for entry in extracted_data:
                for field_key in ["PLATE_NO", "HEAT_NO", "TEST_CERT_NO"]:
                    if entry.get(field_key):
                        ExtractedData.objects.create(
                            vendor=vendor,
                            pdf=uploaded_pdf,
                            field_key=field_key,
                            field_value=entry[field_key]
                        )
                        extraction_count += 1
            
            if extraction_count == 0:
                raise ValidationError("No matching data patterns found in the PDF")
            
            messages.success(request, f"Successfully extracted {extraction_count} fields from the PDF")
            return redirect("dashboard")
            
        except ValidationError as e:
            return render(request, "extractor/upload.html", {
                "vendors": vendors,
                "error": str(e)
            })
        except Exception as e:
            return render(request, "extractor/upload.html", {
                "vendors": vendors,
                "error": f"An unexpected error occurred: {str(e)}"
            })
    
    return render(request, "extractor/upload.html", {"vendors": vendors})
