import os
import logging
from django.http import HttpResponse
from django.views.decorators.http import require_GET
from django.shortcuts import get_object_or_404
from django.contrib.auth.decorators import login_required
from extractor.models import UploadedPDF
from extractor.utils.pdf_zip_utils import create_pdf_specific_package, create_streaming_zip_response, get_extracted_files_info

logger = logging.getLogger(__name__)

@require_GET
@login_required
def download_package_by_filename(request):
    """
    Downloads all extracted PDFs for a given input PDF into a single ZIP and returns it for download.
    Query Parameter: input_pdf (Original uploaded PDF filename)
    """
    input_pdf = request.GET.get('input_pdf')
    
    if not input_pdf:
        return HttpResponse(
            "Missing required parameter: input_pdf", 
            content_type="text/plain", 
            status=400
        )
    
    try:
        # Create the package using utility function
        success, result = create_pdf_specific_package(input_pdf)
        
        if not success:
            return HttpResponse(
                result, 
                content_type="text/plain", 
                status=404
            )
        
        # Get base filename for download
        base_filename = os.path.splitext(os.path.basename(input_pdf))[0]
        
        # Create streaming response
        return create_streaming_zip_response(result, base_filename)
        
    except Exception as e:
        logger.exception(f"Error creating package for {input_pdf}: {str(e)}")
        return HttpResponse(
            f"Error creating package: {str(e)}", 
            content_type="text/plain", 
            status=500
        )

@require_GET  
@login_required
def download_package_by_pdf_id(request, pdf_id):
    """
    Downloads all extracted PDFs for a given UploadedPDF ID into a single ZIP.
    URL Parameter: pdf_id (UploadedPDF model ID)
    """
    try:
        # Get the uploaded PDF record
        uploaded_pdf = get_object_or_404(UploadedPDF, id=pdf_id)
        
        # Get the original filename from the uploaded PDF
        original_filename = os.path.basename(uploaded_pdf.pdf_file.name)
        
        # Create the package using utility function
        success, result = create_pdf_specific_package(original_filename)
        
        if not success:
            return HttpResponse(
                result, 
                content_type="text/plain", 
                status=404
            )
        
        # Get base filename for download
        base_filename = os.path.splitext(original_filename)[0]
        
        # Create streaming response
        return create_streaming_zip_response(result, base_filename)
        
    except Exception as e:
        logger.exception(f"Error creating package for PDF ID {pdf_id}: {str(e)}")
        return HttpResponse(
            f"Error creating package: {str(e)}", 
            content_type="text/plain", 
            status=500
        )