
# from celery import shared_task
# import logging
# from .utils.extractor import extract_pdf_fields
# from .models import ExtractedData, UploadedPDF
# from django.conf import settings
# import os

# logger = logging.getLogger('extractor.tasks')

# @shared_task(bind=True)
# def process_pdf_file(self, uploaded_pdf_id, vendor_config):
#     """
#     Celery task to process PDF file asynchronously with progress updates.
#     States:
#       - PENDING
#       - PROGRESS (meta: current, total, phase)
#       - SUCCESS (result: dict)
#       - FAILURE
#     """
#     try:
#         # Phase 1: load
#         self.update_state(state='PROGRESS', meta={'current': 1, 'total': 4, 'phase': 'loading'})
#         uploaded_pdf = UploadedPDF.objects.get(id=uploaded_pdf_id)
#         logger.info(f"Starting PDF processing for {uploaded_pdf.file.name}")

#         # Phase 2: ocr/extraction
#         self.update_state(state='PROGRESS', meta={'current': 2, 'total': 4, 'phase': 'extracting'})
#         extracted_data, extraction_stats = extract_pdf_fields(
#             uploaded_pdf.file.path,
#             vendor_config,
#             output_folder=os.path.join(settings.MEDIA_ROOT, 'extracted')
#         )

#         # Handle no data (complete OCR fallback failure)
#         if not extracted_data:
#             logger.warning("No data extracted from PDF (complete OCR fallback failure)")
#             result = {
#                 "status": "failed_ocr",
#                 "message": "⚠ OCR fallback needed - No data could be extracted",
#                 "pdf_id": uploaded_pdf_id,
#                 "extracted": 0,
#                 "stats": extraction_stats
#             }
#             return result

#         # Phase 3: saving to DB
#         self.update_state(state='PROGRESS', meta={'current': 3, 'total': 4, 'phase': 'saving'})
#         extraction_count = 0
#         for entry in extracted_data:
#             page_number = entry.get('Page', 1)  # Get page number from extraction entry
#             for field_key in ["PLATE_NO", "HEAT_NO", "TEST_CERT_NO"]:
#                 if entry.get(field_key):
#                     ExtractedData.objects.create(
#                         vendor=uploaded_pdf.vendor,
#                         pdf=uploaded_pdf,
#                         field_key=field_key,
#                         field_value=entry[field_key],
#                         page_number=page_number
#                     )
#                     extraction_count += 1
        
#         # Update master Excel file with the new data
#         try:
#             from .utils.update_excel import update_master_excel
#             update_master_excel()
#         except Exception as e:
#             logger.error(f"Error updating master Excel file: {str(e)}", exc_info=True)

#         # Phase 4: finalize
#         self.update_state(state='PROGRESS', meta={'current': 4, 'total': 4, 'phase': 'finalizing'})
#         logger.info(f"Successfully extracted {extraction_count} fields from PDF {uploaded_pdf.file.name}")
        
#         # Determine status based on extraction statistics
#         if extraction_stats["partial_extraction"]:
#             # Partial success with OCR fallback or some failed pages
#             status = "partial_success_ocr"
#             message = "Partial extraction with OCR fallback"
#         else:
#             # Complete success without OCR fallback
#             status = "completed"
#             message = "Extraction completed successfully"
            
#         return {
#             "status": status,
#             "message": message,
#             "pdf_id": uploaded_pdf_id,
#             "extracted": extraction_count,
#             "stats": extraction_stats
#         }

#     except Exception as e:
#         logger.error(f"Error processing PDF: {str(e)}", exc_info=True)
#         return {
#             "status": "failed",
#             "message": "Unexpected error during extraction",
#             "error": str(e),
#             "pdf_id": uploaded_pdf_id
#         }


from celery import shared_task
import logging
from .models import UploadedPDF, ExtractedData
from .utils.extractor import extract_pdf_fields
from django.conf import settings
import os

logger = logging.getLogger('extractor.tasks')

@shared_task(bind=True)
def process_pdf_file(self, uploaded_pdf_id, vendor_config):
    """Celery task for PDF extraction, with robust fallback/status handling"""
    try:
        # Phase 1: Loading PDF (10%)
        self.update_state(state='PROGRESS', meta={
            'phase': 'loading',
            'current': 1,
            'total': 4,
            'progress': 10
        })
        uploaded_pdf = UploadedPDF.objects.get(id=uploaded_pdf_id)
        logger.info(f"Starting extraction for PDF: {uploaded_pdf.file.name}")

        # Phase 2: Extracting data (40%)
        self.update_state(state='PROGRESS', meta={
            'phase': 'extracting',
            'current': 2,
            'total': 4,
            'progress': 40
        })
        extracted_data, extraction_stats = extract_pdf_fields(
            uploaded_pdf.file.path, vendor_config,
            output_folder=os.path.join(settings.MEDIA_ROOT, 'extracted')
        )

        # Fallback: No data extracted
        if not extracted_data:
            uploaded_pdf.status = 'ERROR'
            uploaded_pdf.save()
            logger.warning("No data extracted (OCR fallback)")
            return {
                "status": "failed_ocr",
                "message": "Extraction failed. OCR fallback was needed but could not extract data.",
                "pdf_id": uploaded_pdf_id,
                "extracted": 0,
                "stats": extraction_stats if 'extraction_stats' in locals() else {}
            }

        # Phase 3: Saving to database (80%)
        self.update_state(state='PROGRESS', meta={
            'phase': 'saving',
            'current': 3,
            'total': 4,
            'progress': 80
        })
        extraction_count = 0
        for entry in extracted_data:
            page_number = entry.get('Page', 1)
            for field_key in ["PLATE_NO", "HEAT_NO", "TEST_CERT_NO"]:
                if entry.get(field_key):
                    ExtractedData.objects.create(
                        vendor=uploaded_pdf.vendor,
                        pdf=uploaded_pdf,
                        field_key=field_key,
                        field_value=entry[field_key],
                        page_number=page_number
                    )
                    extraction_count += 1

        uploaded_pdf.status = 'COMPLETED'
        uploaded_pdf.save()
        
        # Phase 4: Finalizing (95%)
        self.update_state(state='PROGRESS', meta={
            'phase': 'finalizing',
            'current': 4,
            'total': 4,
            'progress': 95
        })
        logger.info(f"Extracted {extraction_count} fields from PDF {uploaded_pdf.file.name}")

        result_status = "partial_success_ocr" if extraction_stats.get("partial_extraction") else "completed"
        
        # Prepare a detailed message for display
        if result_status == "partial_success_ocr":
            message = f"Partial extraction: {extraction_count} fields extracted. Some pages required OCR fallback."
        else:
            message = f"Extraction completed successfully! {extraction_count} fields extracted."
            
        # Include any additional details from extraction stats
        details = {}
        if extraction_stats.get("ocr_fallback_pages"):
            details["ocr_pages"] = extraction_stats.get("ocr_fallback_pages")
        if extraction_stats.get("failed_pages"):
            details["failed_pages"] = extraction_stats.get("failed_pages")
            
        return {
            "status": result_status,
            "message": message,
            "pdf_id": uploaded_pdf_id,
            "extracted": extraction_count,
            "details": details,
            "stats": extraction_stats
        }

    except Exception as e:
        logger.error(f"Exception during extraction: {str(e)}", exc_info=True)
        try:
            pdf = UploadedPDF.objects.get(id=uploaded_pdf_id)
            pdf.status = 'ERROR'
            pdf.save()
        except Exception:
            pass
        return {
            "status": "failed",
            "message": f"Extraction failed. Error: {str(e)}",
            "error": str(e),
            "pdf_id": uploaded_pdf_id
        }
