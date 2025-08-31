# from celery import shared_task
# import logging
# from .utils.extractor import extract_pdf_fields
# from .models import ExtractedData, UploadedPDF
# from django.conf import settings
# import os

# logger = logging.getLogger('extractor.tasks')

# @shared_task
# def process_pdf_file(uploaded_pdf_id, vendor_config):
#     """
#     Celery task to process PDF file asynchronously
#     """
#     try:
#         # Get the uploaded PDF
#         uploaded_pdf = UploadedPDF.objects.get(id=uploaded_pdf_id)
#         logger.info(f"Starting PDF processing for {uploaded_pdf.file.name}")

#         # Run extraction
#         extracted_data = extract_pdf_fields(
#             uploaded_pdf.file.path,
#             vendor_config,
#             output_folder=os.path.join(settings.MEDIA_ROOT, 'extracted')
#         )

#         if not extracted_data:
#             logger.warning("No data extracted from PDF")
#             return False

#         # Save extracted data
#         extraction_count = 0
#         for entry in extracted_data:
#             for field_key in ["PLATE_NO", "HEAT_NO", "TEST_CERT_NO"]:
#                 if entry.get(field_key):
#                     ExtractedData.objects.create(
#                         vendor=uploaded_pdf.vendor,
#                         pdf=uploaded_pdf,
#                         field_key=field_key,
#                         field_value=entry[field_key]
#                     )
#                     extraction_count += 1

#         logger.info(f"Successfully extracted {extraction_count} fields from PDF {uploaded_pdf.file.name}")
#         return True

#     except Exception as e:
#         logger.error(f"Error processing PDF: {str(e)}", exc_info=True)
#         return False


# extractor/tasks.py
from celery import shared_task
import logging
from .utils.extractor import extract_pdf_fields
from .models import ExtractedData, UploadedPDF
from django.conf import settings
import os

logger = logging.getLogger('extractor.tasks')

@shared_task(bind=True)
def process_pdf_file(self, uploaded_pdf_id, vendor_config):
    """
    Celery task to process PDF file asynchronously with progress updates.
    States:
      - PENDING
      - PROGRESS (meta: current, total, phase)
      - SUCCESS (result: dict)
      - FAILURE
    """
    try:
        # Phase 1: load
        self.update_state(state='PROGRESS', meta={'current': 1, 'total': 4, 'phase': 'loading'})
        uploaded_pdf = UploadedPDF.objects.get(id=uploaded_pdf_id)
        logger.info(f"Starting PDF processing for {uploaded_pdf.file.name}")

        # Phase 2: ocr/extraction
        self.update_state(state='PROGRESS', meta={'current': 2, 'total': 4, 'phase': 'extracting'})
        extracted_data, extraction_stats = extract_pdf_fields(
            uploaded_pdf.file.path,
            vendor_config,
            output_folder=os.path.join(settings.MEDIA_ROOT, 'extracted')
        )

        # Handle no data (complete OCR fallback failure)
        if not extracted_data:
            logger.warning("No data extracted from PDF (complete OCR fallback failure)")
            result = {
                "status": "failed_ocr",
                "message": "⚠ OCR fallback needed - No data could be extracted",
                "pdf_id": uploaded_pdf_id,
                "extracted": 0,
                "stats": extraction_stats
            }
            return result

        # Phase 3: saving to DB
        self.update_state(state='PROGRESS', meta={'current': 3, 'total': 4, 'phase': 'saving'})
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

        # Phase 4: finalize
        self.update_state(state='PROGRESS', meta={'current': 4, 'total': 4, 'phase': 'finalizing'})
        logger.info(f"Successfully extracted {extraction_count} fields from PDF {uploaded_pdf.file.name}")
        
        # Determine status based on extraction statistics
        if extraction_stats["partial_extraction"]:
            # Partial success with OCR fallback or some failed pages
            status = "partial_success_ocr"
            message = "Partial extraction with OCR fallback"
        else:
            # Complete success without OCR fallback
            status = "completed"
            message = "Extraction completed successfully"
            
        return {
            "status": status,
            "message": message,
            "pdf_id": uploaded_pdf_id,
            "extracted": extraction_count,
            "stats": extraction_stats
        }

    except Exception as e:
        logger.error(f"Error processing PDF: {str(e)}", exc_info=True)
        return {
            "status": "failed",
            "message": "Unexpected error during extraction",
            "error": str(e),
            "pdf_id": uploaded_pdf_id
        }
