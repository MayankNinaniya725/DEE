import os
import io
import json
import logging
import tempfile
import shutil
import zipfile
import hashlib
from datetime import datetime

from django.shortcuts import render, redirect
from django.urls import reverse
from django.core.files.storage import FileSystemStorage
from django.contrib import messages
from django.contrib.auth import logout
from django.db.models import Count, Q
from django.core.exceptions import ValidationError
from django.conf import settings
from django.http import JsonResponse, HttpResponse, FileResponse
from django.utils import timezone
from celery.result import AsyncResult

import pandas as pd
from openpyxl import load_workbook

from .models import ExtractedData, Vendor, UploadedPDF
from .utils.extractor import extract_pdf_fields
from .utils.config_loader import load_vendor_config
from .tasks import process_pdf_file

# Configure logging
logger = logging.getLogger('extractor')


def dashboard(request):
    """Dashboard view showing summary of uploaded PDFs and extraction status"""
    try:
        # Get query parameters
        vendor_id = request.GET.get('vendor')
        status_filter = request.GET.get('status')
        
        # Base query with prefetch for optimization
        pdfs_query = UploadedPDF.objects.select_related('vendor').prefetch_related('extracted_data')
        
        # Apply filters
        if vendor_id:
            try:
                pdfs_query = pdfs_query.filter(vendor_id=int(vendor_id))
            except (ValueError, TypeError):
                pass  # Invalid vendor ID, ignore filter
                
        if status_filter:
            pdfs_query = pdfs_query.filter(status=status_filter.upper())
            
        # Filter by user if not superuser
        if not request.user.is_superuser:
            pdfs_query = pdfs_query.filter(user=request.user)
            
        # Get recent PDFs
        recent_pdfs = pdfs_query.order_by('-uploaded_at')[:10]
        
        # Get vendors with counts for the filter dropdown
        vendors = Vendor.objects.annotate(pdf_count=Count('pdfs'))
        
        # Get status summary for the status filter dropdown
        status_counts = UploadedPDF.objects.values('status').annotate(count=Count('id'))
        status_summary = {status['status']: status['count'] for status in status_counts}
        
        # Process any session messages (from older versions of the code)
        pdf_messages = request.session.pop('pdf_messages', None)
        if pdf_messages:
            # Map our level names to Django's message levels
            level_mapping = {
                'success': messages.SUCCESS,
                'error': messages.ERROR,
                'warning': messages.WARNING,
                'info': messages.INFO
            }
            
            for msg in pdf_messages:
                level = level_mapping.get(msg['level'], messages.INFO)
                
                # Skip adding to messages framework if this message is already there
                # This prevents duplicate messages when using both the old and new approaches
                existing_messages = [str(message) for message in messages.get_messages(request)]
                if msg['message'] not in existing_messages:
                    messages.add_message(request, level, msg['message'])
        
        # Get recent extractions
        extraction_filter = Q()
        if not request.user.is_superuser:
            extraction_filter &= Q(pdf__user=request.user)
        
        recent_extractions = ExtractedData.objects.select_related('pdf', 'vendor').filter(extraction_filter).order_by('-created_at')[:20]
        
        # Prepare data context with additional pdf_id for each item
        data = []
        for pdf in recent_pdfs:
            extracted_data = pdf.extracted_data.all()
            key_fields = {}
            for field in ['PLATE_NO', 'HEAT_NO', 'TEST_CERT_NO']:
                match = next((item for item in extracted_data if item.field_key == field), None)
                key_fields[field] = match.field_value if match else ''
            
            data.append({
                'pdf': pdf,
                'pdf_id': pdf.id,  # Include PDF ID explicitly
                'extracted_count': extracted_data.count(),
                'last_extracted': extracted_data.order_by('-created_at').first(),
                'key_fields': key_fields,
                'PLATE_NO': key_fields.get('PLATE_NO', ''),
                'HEAT_NO': key_fields.get('HEAT_NO', ''),
                'TEST_CERT_NO': key_fields.get('TEST_CERT_NO', ''),
                'Vendor': pdf.vendor.name if pdf.vendor else 'Unknown',
                'Source PDF': pdf.file.name,
                'Created': pdf.uploaded_at.strftime("%Y-%m-%d %H:%M:%S"),
                'Filename': os.path.basename(pdf.file.name),
                'Remarks': pdf.notes or ''
            })
        
        # Get current timestamp for the template
        current_timestamp = timezone.now()
        
        context = {
            'recent_pdfs': recent_pdfs,
            'vendors': vendors,
            'status_summary': status_summary,
            'recent_extractions': recent_extractions,
            'data': data,  # Include the enhanced data context
            'task_id': request.session.get('last_task_id'),
            'now': current_timestamp,
        }
        return render(request, 'extractor/dashboard.html', context)
    except Exception as e:
        logger.exception(f"Error in dashboard view: {str(e)}")
        messages.error(request, f"Error loading dashboard: {str(e)}")
        return render(request, 'extractor/dashboard.html', {'error': str(e)})
