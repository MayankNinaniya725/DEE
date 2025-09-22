import json
import logging
import os
from datetime import datetime
from django.http import JsonResponse
from django.views.decorators.http import require_GET
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from extractor.utils.pdf_zip_utils import get_extracted_files_info
from extractor.models import UploadedPDF, ExtractedData

logger = logging.getLogger(__name__)

@require_GET
@login_required
def get_extracted_files_status(request):
    """
    API endpoint to get information about extracted files for a given input PDF.
    Query Parameter: input_pdf (Original uploaded PDF filename)
    
    Returns JSON with:
    - exists: Whether the extraction directory exists
    - file_count: Number of extracted files
    - total_size: Total size of all files in bytes
    - files: List of file information
    """
    input_pdf = request.GET.get('input_pdf')
    
    if not input_pdf:
        return JsonResponse({
            'error': 'Missing required parameter: input_pdf',
            'status': 'error'
        }, status=400)
    
    try:
        info = get_extracted_files_info(input_pdf)
        
        return JsonResponse({
            'status': 'success',
            'input_pdf': input_pdf,
            'base_filename': info['base_filename'],
            'extraction_directory': info['output_directory'],
            'exists': info['exists'],
            'file_count': info['file_count'],
            'total_size_bytes': info['total_size'],
            'total_size_mb': round(info['total_size'] / (1024 * 1024), 2),
            'files': [
                {
                    'name': f['name'],
                    'relative_path': f['relative_path'],
                    'size_bytes': f['size'],
                    'size_kb': round(f['size'] / 1024, 2)
                } for f in info['files']
            ],
            'download_available': info['exists'] and info['file_count'] > 0
        })
        
    except Exception as e:
        logger.exception(f"Error getting file info for {input_pdf}: {str(e)}")
        return JsonResponse({
            'error': f'Error retrieving file information: {str(e)}',
            'status': 'error'
        }, status=500)

@require_GET
@login_required  
def list_all_extracted_directories(request):
    """
    API endpoint to list all available extraction directories.
    Useful for frontend to show available packages for download.
    """
    try:
        from django.conf import settings
        import os
        
        media_root = os.path.abspath(settings.MEDIA_ROOT)
        extracted_dir = os.path.join(media_root, "extracted")
        
        if not os.path.exists(extracted_dir):
            return JsonResponse({
                'status': 'success',
                'directories': [],
                'count': 0,
                'message': 'No extraction directory found'
            })
        
        directories = []
        for item in os.listdir(extracted_dir):
            item_path = os.path.join(extracted_dir, item)
            if os.path.isdir(item_path):
                # Get file count and total size for this directory
                file_count = 0
                total_size = 0
                
                for root, _, files in os.walk(item_path):
                    for file in files:
                        file_path = os.path.join(root, file)
                        if os.path.exists(file_path):
                            file_count += 1
                            total_size += os.path.getsize(file_path)
                
                directories.append({
                    'name': item,
                    'path': item_path,
                    'file_count': file_count,
                    'total_size_bytes': total_size,
                    'total_size_mb': round(total_size / (1024 * 1024), 2),
                    'download_available': file_count > 0
                })
        
        # Sort by name
        directories.sort(key=lambda x: x['name'])
        
        return JsonResponse({
            'status': 'success',
            'directories': directories,
            'count': len(directories)
        })
        
    except Exception as e:
        logger.exception(f"Error listing extraction directories: {str(e)}")
        return JsonResponse({
            'error': f'Error listing directories: {str(e)}',
            'status': 'error'
        }, status=500)


@require_GET
@login_required
def get_latest_pdfs(request):
    """API endpoint to get latest PDF updates for dashboard auto-refresh"""
    try:
        # Get the timestamp from request to only return newer PDFs
        since_timestamp = request.GET.get('since')
        
        if since_timestamp:
            try:
                since_dt = datetime.fromisoformat(since_timestamp.replace('Z', '+00:00'))
                pdfs = UploadedPDF.objects.filter(uploaded_at__gt=since_dt).order_by('-uploaded_at')
            except (ValueError, TypeError):
                # If invalid timestamp, get last 10 PDFs
                pdfs = UploadedPDF.objects.all().order_by('-uploaded_at')[:10]
        else:
            # Get latest 10 PDFs if no timestamp provided
            pdfs = UploadedPDF.objects.all().order_by('-uploaded_at')[:10]
        
        # Prepare PDF data for JSON response
        pdf_data = []
        for pdf in pdfs:
            # Count extracted fields for this PDF
            field_count = ExtractedData.objects.filter(pdf=pdf).count()
            
            pdf_info = {
                'id': pdf.id,
                'filename': os.path.basename(pdf.file.name) if pdf.file.name else 'N/A',
                'vendor_name': pdf.vendor.name if pdf.vendor else 'N/A',
                'status': pdf.status,
                'uploaded_at': pdf.uploaded_at.isoformat(),
                'uploaded_at_display': pdf.uploaded_at.strftime('%Y-%m-%d %H:%M:%S'),
                'field_count': field_count
            }
            pdf_data.append(pdf_info)
        
        return JsonResponse({
            'status': 'success',
            'pdfs': pdf_data,
            'count': len(pdf_data),
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error getting latest PDFs: {str(e)}", exc_info=True)
        return JsonResponse({
            'status': 'error',
            'message': f'Error retrieving PDF updates: {str(e)}'
        }, status=500)