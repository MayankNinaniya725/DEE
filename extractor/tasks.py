from celery import shared_task
import logging
from .utils.extractor import extract_pdf_fields
from .models import ExtractedData, UploadedPDF
from django.conf import settings
import os

logger = logging.getLogger('extractor.tasks')

@shared_task
def process_pdf_file(uploaded_pdf_id, vendor_config):
    """
    Celery task to process PDF file asynchronously
    """
    try:
        # Get the uploaded PDF
        uploaded_pdf = UploadedPDF.objects.get(id=uploaded_pdf_id)
        logger.info(f"Starting PDF processing for {uploaded_pdf.file.name}")

        # Run extraction
        extracted_data = extract_pdf_fields(
            uploaded_pdf.file.path,
            vendor_config,
            output_folder=os.path.join(settings.MEDIA_ROOT, 'extracted')
        )

        if not extracted_data:
            logger.warning("No data extracted from PDF")
            return False

        # Save extracted data
        extraction_count = 0
        for entry in extracted_data:
            for field_key in ["PLATE_NO", "HEAT_NO", "TEST_CERT_NO"]:
                if entry.get(field_key):
                    ExtractedData.objects.create(
                        vendor=uploaded_pdf.vendor,
                        pdf=uploaded_pdf,
                        field_key=field_key,
                        field_value=entry[field_key]
                    )
                    extraction_count += 1

        logger.info(f"Successfully extracted {extraction_count} fields from PDF {uploaded_pdf.file.name}")
        return True

    except Exception as e:
        logger.error(f"Error processing PDF: {str(e)}", exc_info=True)
        return False
