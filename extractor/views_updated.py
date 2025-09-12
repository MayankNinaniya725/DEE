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

def store_dashboard_message(request, message, level='info', extra_data=None):
    """Store message in session for dashboard display"""
    if not request.session.get('pdf_messages', []):
        request.session['pdf_messages'] = []
    request.session['pdf_messages'].append({
        'message': message,
        'level': level,
        'timestamp': timezone.now().isoformat(),
        'extra_data': extra_data or {}
    })
    request.session.modified = True

def process_pdf(request):
    """Handle PDF upload and processing with duplicate detection and vendor validation"""
    if request.method == 'POST' and request.FILES.get('pdf'):
        vendor_id = request.POST.get('vendor')
        pdf_file = request.FILES['pdf']
        
        try:
            vendor = Vendor.objects.get(id=vendor_id)
            
            # Calculate file hash for duplicate detection
            file_content = pdf_file.read()
            file_hash = hashlib.md5(file_content).hexdigest()
            pdf_file.seek(0)
            
            # Check for duplicates with different vendors
            existing_pdfs = UploadedPDF.objects.filter(file_hash=file_hash)
            if existing_pdfs.exists():
                existing_pdf = existing_pdfs.first()
                if existing_pdf.vendor != vendor:
                    msg = f"PDF already exists with vendor '{existing_pdf.vendor.name}'. Please verify the correct vendor."
                    store_dashboard_message(
                        request, msg, 'warning',
                        {'original_vendor': existing_pdf.vendor.name, 'new_vendor': vendor.name}
                    )
                    return JsonResponse({'error': msg, 'type': 'vendor_mismatch'}, status=400)
                
                # Same vendor duplicate handling
                store_dashboard_message(
                    request,
                    f"Duplicate PDF found (uploaded {existing_pdf.uploaded_at.strftime('%Y-%m-%d %H:%M:%S')})",
                    'info'
                )
                
                if existing_pdf.status != 'COMPLETED':
                    try:
                        # Retry extraction
                        config_path = os.path.join(settings.VENDOR_CONFIGS_DIR, vendor.config_file.name)
                        vendor_config = load_vendor_config(config_path)
                        task = process_pdf_file.delay(existing_pdf.id, vendor_config)
                        store_dashboard_message(request, "Retrying extraction for duplicate PDF", 'info')
                        return JsonResponse({
                            'message': 'Duplicate PDF detected, retrying extraction.',
                            'task_id': task.id
                        })
                    except Exception as e:
                        logger.error(f"Error retrying extraction: {str(e)}", exc_info=True)
                        store_dashboard_message(request, "Error retrying extraction", 'error')
                        return JsonResponse({
                            'error': 'Error retrying extraction',
                            'type': 'extraction_error'
                        }, status=500)
                
                return JsonResponse({
                    'error': 'Duplicate PDF already processed',
                    'type': 'duplicate'
                }, status=400)
            
            # Save new PDF
            pdf = UploadedPDF.objects.create(
                file=pdf_file,
                vendor=vendor,
                file_hash=file_hash,
                file_size=pdf_file.size,
                status='PROCESSING',
                user=request.user if not request.user.is_anonymous else None
            )
            
            # Load and validate vendor config
            config_path = os.path.join(settings.VENDOR_CONFIGS_DIR, vendor.config_file.name) if vendor.config_file else None
            if not config_path or not os.path.exists(config_path):
                pdf.status = 'ERROR'
                pdf.save()
                msg = f"Missing vendor configuration for '{vendor.name}'"
                store_dashboard_message(request, msg, 'error')
                return JsonResponse({'error': msg, 'type': 'validation'}, status=400)
            
            try:
                vendor_config = load_vendor_config(config_path)
            except Exception as e:
                logger.error(f"Error loading vendor config: {str(e)}", exc_info=True)
                pdf.status = 'ERROR'
                pdf.save()
                msg = f"Invalid vendor configuration for '{vendor.name}'"
                store_dashboard_message(request, msg, 'error')
                return JsonResponse({'error': msg, 'type': 'validation'}, status=400)
            
            # Start extraction
            task = process_pdf_file.delay(pdf.id, vendor_config)
            store_dashboard_message(request, "PDF uploaded successfully, starting extraction", 'success')
            
            # Store task ID in session for dashboard progress tracking
            request.session['last_task_id'] = task.id
            request.session.modified = True
            
            return JsonResponse({
                'message': 'PDF uploaded successfully',
                'task_id': task.id
            })
            
        except Vendor.DoesNotExist:
            store_dashboard_message(request, "Selected vendor not found", 'error')
            return JsonResponse({
                'error': 'Selected vendor not found',
                'type': 'validation'
            }, status=400)
        except Exception as e:
            logger.error(f"Error processing PDF: {str(e)}", exc_info=True)
            store_dashboard_message(request, "Error processing PDF", 'error')
            return JsonResponse({
                'error': 'Error processing PDF file',
                'type': 'error'
            }, status=500)
    
    return JsonResponse({
        'error': 'Invalid request',
        'type': 'error'
    }, status=400)

def dashboard(request):
    """Dashboard view showing summary of uploaded PDFs and extraction status"""
    # Get all PDFs if admin, otherwise filter by user
    if request.user.is_superuser:
        recent_pdfs = UploadedPDF.objects.select_related('vendor').order_by('-uploaded_at')[:20]
    else:
        recent_pdfs = UploadedPDF.objects.filter(user=request.user).select_related('vendor').order_by('-uploaded_at')[:20]
    
    vendors = Vendor.objects.annotate(pdf_count=Count('pdfs'))
    
    # Get status summary
    status_filter = Q()
    if not request.user.is_superuser:
        status_filter &= Q(user=request.user)
    
    status_summary = {
        'pending': UploadedPDF.objects.filter(status_filter & Q(status='PENDING')).count(),
        'processing': UploadedPDF.objects.filter(status_filter & Q(status='PROCESSING')).count(),
        'completed': UploadedPDF.objects.filter(status_filter & Q(status='COMPLETED')).count(),
        'error': UploadedPDF.objects.filter(status_filter & Q(status='ERROR')).count(),
    }
    
    # Get messages from session
    dashboard_messages = request.session.pop('pdf_messages', [])
    
    # Add messages to Django's message framework
    for msg in dashboard_messages:
        level = {
            'success': messages.SUCCESS,
            'error': messages.ERROR,
            'warning': messages.WARNING,
            'info': messages.INFO
        }.get(msg['level'], messages.INFO)
        messages.add_message(request, level, msg['message'])
    
    # Get recent extractions
    extraction_filter = Q()
    if not request.user.is_superuser:
        extraction_filter &= Q(pdf__user=request.user)
    
    recent_extractions = ExtractedData.objects.select_related(
        'pdf', 'vendor'
    ).filter(
        extraction_filter
    ).order_by('-created_at')[:20]
    
    context = {
        'recent_pdfs': recent_pdfs,
        'vendors': vendors,
        'status_summary': status_summary,
        'recent_extractions': recent_extractions,
        'task_id': request.session.get('last_task_id'),
    }
    return render(request, 'extractor/dashboard.html', context)
